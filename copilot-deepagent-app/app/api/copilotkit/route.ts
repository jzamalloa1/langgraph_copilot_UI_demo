import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { LangGraphAgent } from "@copilotkit/runtime/langgraph";
import { NextRequest } from "next/server";

const serviceAdapter = new ExperimentalEmptyAdapter();

if (!process.env.LANGGRAPH_DEPLOYMENT_URL) {
  throw new Error("LANGGRAPH_DEPLOYMENT_URL environment variable is required");
}
if (!process.env.LANGSMITH_API_KEY) {
  throw new Error("LANGSMITH_API_KEY environment variable is required");
}

const runtime = new CopilotRuntime({
  agents: {
    my_agent: new LangGraphAgent({
      deploymentUrl: process.env.LANGGRAPH_DEPLOYMENT_URL,
      graphId: "my_agent",
      langsmithApiKey: process.env.LANGSMITH_API_KEY,
      // Set recursion_limit via assistantConfig to override CopilotKit's default of 25
      assistantConfig: {
        recursion_limit: 100,
      },
    }),
  }
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};