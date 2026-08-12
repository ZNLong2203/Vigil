import { TRACE } from "@/lib/mock";
import { TraceExplorer } from "@/components/TraceExplorer";

export default function TracePage() {
  return <TraceExplorer trace={TRACE} />;
}
