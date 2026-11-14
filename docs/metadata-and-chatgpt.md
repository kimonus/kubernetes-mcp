# MCP identity and ChatGPT

The server implements stateless Streamable HTTP and negotiates MCP `2025-03-26` using its own implementation rather than a server SDK. Its `initialize` result contains the stable name `kubernetes-mcp`, implementation version `0.1.0`, usage instructions and additional descriptive identity metadata. The Apache-2.0 license is in the repository's [LICENSE](../LICENSE), and the project is maintained in the [kimonus/kubernetes-mcp repository](https://github.com/kimonus/kubernetes-mcp). No separate author or publisher identity is asserted.

For this protocol version, `serverInfo.name` and `serverInfo.version` and tool annotations are defined by the [2025-03-26 schema](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/schema/2025-03-26/schema.json). The optional title, description, website URL and icon on `serverInfo` are forward-compatible extension fields; standardized identity icons and those fields are specified in the later [2025-11-25 schema](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/schema/2025-11-25/schema.json). Clients negotiating 2025-03-26 may ignore them. The server does not advertise the later protocol solely to expose branding. Tool display titles use the supported `annotations.title`; `readOnlyHint` describes intended behavior and does not replace authentication or RBAC.

The repository-owned PNG icon is `src/assets/icon.png` (128 × 128, `image/png`). The initialization response embeds it as a `data:` URI, so it requires no external fetch, public origin endpoint, Kubernetes credential, or private hostname. A client must support the extension and data URIs to display it; protocol-level presence is not evidence of display.

## ChatGPT custom app

[OpenAI's custom MCP server documentation](https://developers.openai.com/api/docs/guides/custom-mcp-server) says the person connecting a custom server enters its name and optional description, and that refreshing the app pulls new tools, descriptions and server instructions. The name and description entered in ChatGPT are registration settings; the server cannot guarantee that its optional identity fields or icon replace them. The connected client has been observed to consume server tool descriptions, but icon and title rendering have not been verified in the ChatGPT UI.

For an existing app after deployment:

1. Open the custom app's settings/details in ChatGPT, and refresh its tools to retrieve updated definitions and descriptions.
2. If the app's registration UI offers name and description editing, use **Kubernetes Diagnostics MCP** and the description in `src/metadata.py`; save the changes. If it does not, use the settings provided for that connection. Do not recreate or disconnect a working app merely to refresh tools.
3. Check the app's displayed icon in the client. If the client provides an icon upload or an app-directory registration field, the repository PNG can be supplied there; do not assume that it reads the server's embedded icon. The availability of this setting and icon rendering has not been verified for this connection.
