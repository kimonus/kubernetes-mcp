// Run with MCP_TS_SDK pointing at the installed SDK's dist/esm directory.
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

const sdk = process.env.MCP_TS_SDK;
if (!sdk) throw new Error('MCP_TS_SDK is required');
const { Client } = await import(pathToFileURL(resolve(sdk, 'client/index.js')).href);
const { StreamableHTTPClientTransport } = await import(pathToFileURL(resolve(sdk, 'client/streamableHttp.js')).href);
const client = new Client({ name: 'typescript-smoke', version: '1.0.0' });
const transport = new StreamableHTTPClientTransport(new URL(process.argv[2]), {
  requestInit: { headers: { Authorization: `Bearer ${'x'.repeat(32)}` } },
});
try {
  await client.connect(transport);
  const tools = await client.listTools();
  if (tools.tools.length !== 5) throw new Error('Unexpected tool count');
  const result = await client.callTool({ name: 'list_pods', arguments: { namespace: 'allowed' } });
  if (result.isError) throw new Error('Tool call failed');
} finally {
  await client.close();
}
