import io
import unittest
import urllib.error

from src.diagnostics import TOOL_SCHEMAS, call_diagnostic


def error(code):
    return urllib.error.HTTPError("https://invalid", code, "error", {}, io.BytesIO())


class FakeKube:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, path, query=None, raw=False):
        self.calls.append((path, query, raw))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class DiagnosticsTests(unittest.TestCase):
    def call(self, kube, name, args, namespaces=None):
        return call_diagnostic(kube, namespaces or {"allowed"}, name, args, cluster_scoped=namespaces == {"*"})

    def test_workload_pagination_and_redaction(self):
        obj = {"items": [{"metadata": {"name": "web", "namespace": "allowed"},
                          "spec": {"replicas": 2, "template": {"secret": "hidden"}},
                          "status": {"readyReplicas": 1, "conditions": [{"reason": "ProgressDeadlineExceeded"}]}}],
               "metadata": {"continue": "opaque"}}
        for kind in ("deployment", "statefulset", "daemonset", "job", "cronjob"):
            k = FakeKube([obj])
            result = self.call(k, "list_workloads", {"namespace": "allowed", "kind": kind, "continue": "cursor"})
            self.assertEqual(result["continue"], "opaque")
            self.assertEqual(k.calls[0][1]["continue"], "cursor")
            self.assertNotIn("secret", repr(result))
            self.assertEqual(result["workloads"][0]["status"]["conditions"][0]["reason"], "ProgressDeadlineExceeded")

    def test_workload_detail_and_missing(self):
        k = FakeKube([{"metadata": {"name": "web"}, "status": {"failed": 1}}])
        result = self.call(k, "get_workload_details", {"namespace": "allowed", "kind": "job", "name": "web"})
        self.assertEqual(result["workload"]["status"]["failed"], 1)
        self.assertTrue(k.calls[0][0].endswith("/jobs/web"))
        with self.assertRaises(urllib.error.HTTPError) as captured:
            self.call(FakeKube([error(404)]), "get_workload_details", {"namespace": "allowed", "kind": "job", "name": "gone"})
        captured.exception.close()

    def test_services_endpoint_readiness_and_denial(self):
        services = {"items": [{"metadata": {"name": "one"}, "spec": {"ports": [{"port": 80}]}},
                               {"metadata": {"name": "two"}, "spec": {}}]}
        k = FakeKube([services, {"subsets": [{"addresses": [{"ip": "private"}], "notReadyAddresses": [{}]}]}, error(403)])
        result = self.call(k, "list_services", {"namespace": "allowed"})
        self.assertEqual(result["services"][0]["endpoints"], {"ready": 1, "not_ready": 1})
        self.assertEqual(result["services"][1]["endpoints"], {"available": False})
        self.assertNotIn("private", repr(result))

    def test_node_status_requires_cluster_scope(self):
        obj = {"metadata": {"name": "n"}, "status": {"conditions": [{"type": "MemoryPressure", "status": "True"}]}}
        with self.assertRaises(ValueError):
            self.call(FakeKube([obj]), "get_node_status", {"name": "n"})
        result = self.call(FakeKube([obj]), "get_node_status", {"name": "n"}, {"*"})
        self.assertEqual(result["conditions"][0]["type"], "MemoryPressure")
        result = call_diagnostic(FakeKube([obj]), {"allowed"}, "get_node_status", {"name": "n"}, cluster_scoped=True)
        self.assertEqual(result["conditions"][0]["type"], "MemoryPressure")
        with self.assertRaises(ValueError):
            call_diagnostic(FakeKube([obj]), {"*"}, "get_node_status", {"name": "n"}, cluster_scoped=False)

    def test_node_discovery_pagination(self):
        k = FakeKube([{"items": [{"metadata": {"name": "n"}, "status": {"conditions": [{"type": "Ready", "status": "True"}]}}],
                       "metadata": {"continue": "next"}}])
        result = self.call(k, "list_nodes", {"continue": "cursor"}, {"*"})
        self.assertEqual(result["nodes"][0]["name"], "n")
        self.assertEqual(result["continue"], "next")
        self.assertEqual(k.calls[0][1]["continue"], "cursor")
        with self.assertRaises(ValueError):
            self.call(FakeKube([]), "list_nodes", {})

    def test_metrics_unavailable_empty_and_denied(self):
        for code in (404, 503):
            result = self.call(FakeKube([error(code)]), "list_pod_metrics", {"namespace": "allowed"})
            self.assertFalse(result["available"])
        result = self.call(FakeKube([{"items": []}]), "list_node_metrics", {}, {"*"})
        self.assertEqual(result["nodes"], [])
        with self.assertRaises(urllib.error.HTTPError) as captured:
            self.call(FakeKube([error(403)]), "list_node_metrics", {}, {"*"})
        captured.exception.close()

    def test_metrics_sanitized(self):
        metrics = {"items": [{"metadata": {"name": "p", "namespace": "allowed"},
                               "containers": [{"name": "app", "usage": {"cpu": "1m", "memory": "2Mi", "secret": "x"}}]}]}
        result = self.call(FakeKube([metrics]), "list_pod_metrics", {"namespace": "allowed"})
        self.assertEqual(result["pods"][0]["containers"][0]["usage"], {"cpu": "1m", "memory": "2Mi"})

    def test_node_metrics_and_page_limit_if_server_ignores_limit(self):
        values = [{"metadata": {"name": f"n{i}"}, "usage": {"cpu": "1m", "memory": "2Mi"}} for i in range(7)]
        k = FakeKube([{"items": values}])
        result = self.call(k, "list_node_metrics", {"continue": "cursor"}, {"*"})
        self.assertEqual(len(result["nodes"]), 5)
        self.assertTrue(result["truncated"])
        self.assertIsNone(result["continue"])
        self.assertEqual(k.calls[0][1], {"limit": 5, "continue": "cursor"})

    def test_named_metrics_access_when_server_does_not_paginate(self):
        k = FakeKube([{"metadata": {"name": "sixth"}, "usage": {"cpu": "1m"}}])
        result = self.call(k, "list_node_metrics", {"name": "sixth"}, {"*"})
        self.assertEqual(result["nodes"][0]["name"], "sixth")
        self.assertTrue(k.calls[0][0].endswith("/nodes/sixth"))
        k = FakeKube([{"metadata": {"name": "sixth"}, "containers": []}])
        result = self.call(k, "list_pod_metrics", {"namespace": "allowed", "name": "sixth"})
        self.assertEqual(result["pods"][0]["name"], "sixth")
        self.assertTrue(k.calls[0][0].endswith("/pods/sixth"))
        with self.assertRaises(ValueError):
            self.call(FakeKube([]), "list_pod_metrics", {"namespace": "allowed", "name": "p", "continue": "cursor"})

    def test_denials_and_missing_pods_are_not_treated_as_empty(self):
        for name, args in (("list_services", {"namespace": "allowed"}),
                           ("list_workloads", {"namespace": "allowed", "kind": "deployment"}),
                           ("diagnose_pod", {"namespace": "allowed", "pod": "gone"})):
            for code in (403, 404):
                with self.subTest(name=name, code=code), self.assertRaises(urllib.error.HTTPError) as captured:
                    self.call(FakeKube([error(code)]), name, args)
                captured.exception.close()

    def test_service_and_pod_metrics_pagination_and_namespace(self):
        k = FakeKube([{"items": [], "metadata": {"continue": "next"}}])
        result = self.call(k, "list_services", {"namespace": "allowed", "continue": "before"})
        self.assertEqual(result, {"services": [], "continue": "next", "truncated": True})
        self.assertEqual(k.calls[0][1]["continue"], "before")
        k = FakeKube([{"items": [], "metadata": {"continue": "next"}}])
        result = self.call(k, "list_pod_metrics", {"namespace": "allowed", "continue": "before"})
        self.assertEqual(result["continue"], "next")
        self.assertIn("/namespaces/allowed/pods", k.calls[0][0])
        self.assertEqual(k.calls[0][1]["continue"], "before")

    def test_pod_event_uid_required_and_logs_denials_propagate(self):
        with self.assertRaises(ValueError):
            self.call(FakeKube([{"metadata": {}}]), "diagnose_pod", {"namespace": "allowed", "pod": "p"})
        pod = {"metadata": {"uid": "uid"}, "status": {"containerStatuses": [{"name": "a", "restartCount": 1}]}}
        with self.assertRaises(urllib.error.HTTPError) as captured:
            self.call(FakeKube([pod, {"items": []}, error(403)]), "diagnose_pod", {"namespace": "allowed", "pod": "p"})
        captured.exception.close()

    def test_diagnose_multiple_containers_previous_and_bounded_logs(self):
        pod = {"metadata": {"name": "p", "uid": "uid"}, "status": {"phase": "Pending", "containerStatuses": [
            {"name": "a", "restartCount": 1, "state": {"waiting": {"reason": "ImagePullBackOff"}},
             "lastState": {"terminated": {"reason": "OOMKilled", "exitCode": 137}}},
            {"name": "b", "restartCount": 0}, {"name": "c", "restartCount": 0}]}}
        events = {"items": [{"reason": "FailedScheduling", "message": "full"}], "metadata": {"continue": "next"}}
        k = FakeKube([pod, events, "x" * 5000, error(400), "current"])
        out = self.call(k, "diagnose_pod", {"namespace": "allowed", "pod": "p"})
        self.assertEqual(out["pod"]["containers"][0]["last_state"]["terminated"]["reason"], "OOMKilled")
        self.assertEqual(len(out["logs"][0]["untrusted_log_text"]), 2048)
        self.assertFalse(out["logs"][1]["available"])
        self.assertTrue(out["logs_truncated"])
        self.assertTrue(out["events_truncated"])
        self.assertEqual(k.calls[1][1]["fieldSelector"], "involvedObject.uid=uid")
        self.assertEqual(k.calls[2][1]["limitBytes"], 2048)

    def test_arguments_and_namespace_fail_closed(self):
        for name, args in [("list_services", {"namespace": "other"}),
                           ("list_workloads", {"namespace": "allowed", "kind": "pods"}),
                           ("diagnose_pod", {"namespace": "allowed", "pod": "../x"}),
                           ("list_pod_metrics", {"namespace": "allowed", "continue": "x" * 2049}),
                           ("list_node_metrics", {"unexpected": "x"})]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.call(FakeKube([]), name, args)
        self.assertEqual(set(TOOL_SCHEMAS), {"list_workloads", "get_workload_details", "list_services", "list_nodes", "get_node_status",
                                            "list_node_metrics", "list_pod_metrics", "diagnose_pod"})


if __name__ == "__main__":
    unittest.main()
