"""Bounded read-only Kubernetes workload and cluster diagnostics."""
import re
import urllib.error
import urllib.parse

NAME = re.compile(r"^[a-z0-9](?:[-a-z0-9.]*[a-z0-9])?$")
KINDS = {
    "deployment": ("apps/v1", "deployments"),
    "statefulset": ("apps/v1", "statefulsets"),
    "daemonset": ("apps/v1", "daemonsets"),
    "job": ("batch/v1", "jobs"),
    "cronjob": ("batch/v1", "cronjobs"),
}


def schema(properties, required):
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


string = {"type": "string", "maxLength": 253}
cursor = {"type": "string", "maxLength": 2048}
kind = {"type": "string", "enum": list(KINDS)}
TOOL_SCHEMAS = {
    "list_workloads": schema({"namespace": string, "kind": kind, "continue": cursor}, ["namespace", "kind"]),
    "get_workload_details": schema({"namespace": string, "kind": kind, "name": string}, ["namespace", "kind", "name"]),
    "list_services": schema({"namespace": string, "continue": cursor}, ["namespace"]),
    "list_nodes": schema({"continue": cursor}, []),
    "get_node_status": schema({"name": string}, ["name"]),
    "list_node_metrics": schema({"name": string, "continue": cursor}, []),
    "list_pod_metrics": schema({"namespace": string, "name": string, "continue": cursor}, ["namespace"]),
    "diagnose_pod": schema({"namespace": string, "pod": string}, ["namespace", "pod"]),
}


def short(value, limit=512):
    return value[:limit] if isinstance(value, str) else value


def subset(obj, keys):
    return {key: short(obj[key]) for key in keys if key in obj}


def _validate(args, name, namespaces, cluster_scoped):
    if not isinstance(args, dict):
        raise ValueError("Invalid arguments")
    definition = TOOL_SCHEMAS[name]
    if set(args) - set(definition["properties"]) or set(definition["required"]) - set(args):
        raise ValueError("Invalid arguments")
    for key, value in args.items():
        if not isinstance(value, str) or not value:
            raise ValueError("Invalid argument")
        if key == "continue":
            if len(value) > 2048:
                raise ValueError("Invalid continuation token")
        elif key == "kind":
            if value not in KINDS:
                raise ValueError("Invalid workload kind")
        elif len(value) > 253 or not NAME.fullmatch(value):
            raise ValueError("Invalid resource name")
    if "namespace" in args and "*" not in namespaces and args["namespace"] not in namespaces:
        raise ValueError("Namespace not allowed")
    if name in ("list_nodes", "get_node_status", "list_node_metrics") and not cluster_scoped:
        raise ValueError("Cluster scope is not enabled")
    if name in ("list_node_metrics", "list_pod_metrics") and "name" in args and "continue" in args:
        raise ValueError("A named metrics request cannot use a continuation token")


def page_query(args, limit=5):
    query = {"limit": limit}
    if args.get("continue"):
        query["continue"] = args["continue"]
    return query


def page(result, key, values):
    token = (result.get("metadata") or {}).get("continue") or None
    return {key: values, "continue": token,
            "truncated": bool(token) or len(result.get("items") or []) > len(values)}


def workload_summary(obj):
    meta, spec, status = obj.get("metadata") or {}, obj.get("spec") or {}, obj.get("status") or {}
    return {"name": short(meta.get("name")), "namespace": short(meta.get("namespace")),
            "generation": meta.get("generation"),
            "desired_replicas": spec.get("replicas"),
            "status": {**subset(status, ("observedGeneration", "replicas", "readyReplicas", "availableReplicas",
                                          "updatedReplicas", "unavailableReplicas", "currentReplicas", "desiredNumberScheduled",
                                          "numberReady", "numberAvailable", "numberUnavailable", "succeeded", "failed", "active",
                                          "lastScheduleTime", "lastSuccessfulTime")),
                       "conditions": [subset(c, ("type", "status", "reason", "message"))
                                      for c in (status.get("conditions") or [])[:10]]}}


def pod_status(obj):
    meta, status = obj.get("metadata") or {}, obj.get("status") or {}
    statuses = (status.get("initContainerStatuses") or []) + (status.get("containerStatuses") or [])
    containers = []
    for c in statuses[:20]:
        def state(value):
            return {phase: subset(value[phase], ("reason", "message", "exitCode", "startedAt", "finishedAt"))
                    for phase in ("waiting", "running", "terminated") if isinstance(value.get(phase), dict)}
        containers.append({**subset(c, ("name", "ready", "restartCount")),
                           "state": state(c.get("state") or {}), "last_state": state(c.get("lastState") or {})})
    return {"name": short(meta.get("name")), "namespace": short(meta.get("namespace")),
            "phase": short(status.get("phase")), "reason": short(status.get("reason")),
            "conditions": [subset(c, ("type", "status", "reason", "message"))
                           for c in (status.get("conditions") or [])[:10]], "containers": containers,
            "containers_truncated": len(statuses) > 20}


def _metrics(kube, path, args, nodes):
    try:
        if args.get("name"):
            result = {"items": [kube.get(path + "/" + urllib.parse.quote(args["name"], safe=""))]}
        else:
            result = kube.get(path, page_query(args))
    except urllib.error.HTTPError as exc:
        if exc.code in (404, 503):
            exc.close()
            return {"available": False,
                    "reason": "Metrics API or resource unavailable" if args.get("name") else "Metrics API unavailable"}
        raise
    items = []
    for item in result.get("items", [])[:5]:
        meta = item.get("metadata") or {}
        value = {"name": short(meta.get("name")), "timestamp": short(item.get("timestamp")),
                 "window": short(item.get("window"))}
        if nodes:
            value["usage"] = subset(item.get("usage") or {}, ("cpu", "memory"))
        else:
            value["namespace"] = short(meta.get("namespace"))
            value["containers"] = [dict(subset(c, ("name",)), usage=subset(c.get("usage") or {}, ("cpu", "memory")))
                                   for c in (item.get("containers") or [])[:20]]
        items.append(value)
    return {"available": True, **page(result, "nodes" if nodes else "pods", items)}


def call_diagnostic(kube, namespaces, name, args, cluster_scoped=False):
    _validate(args, name, namespaces, cluster_scoped)
    ns = urllib.parse.quote(args.get("namespace", ""), safe="")
    root = "/api/v1/namespaces/" + ns
    if name in ("list_workloads", "get_workload_details"):
        group, plural = KINDS[args["kind"]]
        path = "/apis/" + group + "/namespaces/" + ns + "/" + plural
        if name == "get_workload_details":
            return {"kind": args["kind"], "workload": workload_summary(kube.get(path + "/" + urllib.parse.quote(args["name"], safe="")))}
        result = kube.get(path, page_query(args))
        return {"kind": args["kind"], **page(result, "workloads", [workload_summary(x) for x in result.get("items", [])[:5]])}
    if name == "list_services":
        result = kube.get(root + "/services", page_query(args))
        values = []
        for service in result.get("items", [])[:5]:
            meta, spec = service.get("metadata") or {}, service.get("spec") or {}
            item = {"name": short(meta.get("name")), "namespace": short(meta.get("namespace")),
                    "type": short(spec.get("type")), "ports": [subset(x, ("name", "port", "protocol", "targetPort"))
                                                             for x in (spec.get("ports") or [])[:20]]}
            try:
                endpoint = kube.get(root + "/endpoints/" + urllib.parse.quote(meta.get("name", ""), safe=""))
                subsets = endpoint.get("subsets") or []
                item["endpoints"] = {"ready": sum(len(s.get("addresses") or []) for s in subsets),
                                     "not_ready": sum(len(s.get("notReadyAddresses") or []) for s in subsets)}
            except urllib.error.HTTPError as exc:
                if exc.code not in (403, 404):
                    raise
                exc.close()
                item["endpoints"] = {"available": False}
            values.append(item)
        return page(result, "services", values)
    if name == "list_nodes":
        result = kube.get("/api/v1/nodes", page_query(args))
        values = []
        for node in result.get("items", [])[:5]:
            meta, spec, status = node.get("metadata") or {}, node.get("spec") or {}, node.get("status") or {}
            values.append({"name": short(meta.get("name")), "unschedulable": bool(spec.get("unschedulable")),
                           "conditions": [subset(c, ("type", "status", "reason"))
                                          for c in (status.get("conditions") or [])[:15]]})
        return page(result, "nodes", values)
    if name == "get_node_status":
        obj = kube.get("/api/v1/nodes/" + urllib.parse.quote(args["name"], safe=""))
        meta, spec, status = obj.get("metadata") or {}, obj.get("spec") or {}, obj.get("status") or {}
        return {"name": short(meta.get("name")), "unschedulable": bool(spec.get("unschedulable")),
                "conditions": [subset(c, ("type", "status", "reason", "message")) for c in (status.get("conditions") or [])[:15]],
                "capacity": subset(status.get("capacity") or {}, ("cpu", "memory", "pods", "ephemeral-storage")),
                "allocatable": subset(status.get("allocatable") or {}, ("cpu", "memory", "pods", "ephemeral-storage"))}
    if name == "list_node_metrics":
        return _metrics(kube, "/apis/metrics.k8s.io/v1beta1/nodes", args, True)
    if name == "list_pod_metrics":
        return _metrics(kube, "/apis/metrics.k8s.io/v1beta1/namespaces/" + ns + "/pods", args, False)
    if name == "diagnose_pod":
        pod = urllib.parse.quote(args["pod"], safe="")
        obj = kube.get(root + "/pods/" + pod)
        uid = (obj.get("metadata") or {}).get("uid")
        if not uid:
            raise ValueError("Pod identity unavailable")
        events = kube.get(root + "/events", {"fieldSelector": "involvedObject.uid=" + uid, "limit": 10})
        result = {"pod": pod_status(obj), "events": [subset(e, ("type", "reason", "message", "count", "lastTimestamp"))
                                                      for e in events.get("items", [])[:10]],
                  "events_truncated": bool((events.get("metadata") or {}).get("continue")) or len(events.get("items") or []) > 10,
                  "logs": []}
        statuses = (obj.get("status") or {}).get("containerStatuses") or []
        for container in statuses[:2]:
            cname = container.get("name")
            if not isinstance(cname, str) or not NAME.fullmatch(cname):
                continue
            for previous in ([False, True] if container.get("restartCount", 0) else [False]):
                query = {"container": cname, "tailLines": 30, "sinceSeconds": 3600,
                         "timestamps": "true", "limitBytes": 2048}
                if previous:
                    query["previous"] = "true"
                try:
                    raw = kube.get(root + "/pods/" + pod + "/log", query, raw=True)
                    entry = {"container": cname, "previous": previous, "available": True,
                             "untrusted_log_text": str(raw)[:2048], "upstream_limit_bytes": 2048,
                             "truncated": True if len(str(raw)) > 2048 or getattr(raw, "truncated", False) else None}
                except urllib.error.HTTPError as exc:
                    if exc.code not in (400, 404):
                        raise
                    exc.close()
                    entry = {"container": cname, "previous": previous, "available": False}
                result["logs"].append(entry)
        result["logs_truncated"] = len(statuses) > 2
        return result
    raise ValueError("Unknown diagnostic tool")
