"use client";

import { useEffect, useState, useCallback } from "react";

import { DashboardLayout } from "@/components/ui/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { Shield, Server, Activity, Zap, FileText, Loader2 } from "lucide-react";

export default function SecurityPage() {
  const { ready, authenticated } = useAuthGuard();
  const [scanResult, setScanResult] = useState<any>(null);
  const [scanning, setScanning] = useState(false);
  const [modelPath, setModelPath] = useState("./models");
  const [dashboard, setDashboard] = useState<any>(null);
  const [benchmarkResult, setBenchmarkResult] = useState<any>(null);
  const [benchmarking, setBenchmarking] = useState<string | null>(null);
  const [agents, setAgents] = useState<{ id: string; name: string }[]>([]);
  const [agentId, setAgentId] = useState("");

  const fetchDashboard = useCallback(async () => {
    try {
      const res = await api.get("/security/security-dashboard").catch(() => api.get("/monitoring/dashboard").catch(() => ({ data: null })));
      setDashboard(res.data);
    } catch {}
    api.get("/agents").then((res) => setAgents(res.data)).catch(() => setAgents([]));
  }, []);

  useEffect(() => {
    if (!ready || !authenticated) return;
    void fetchDashboard();
  }, [ready, authenticated, fetchDashboard]);

  const handleScan = async () => {
    setScanning(true);
    try {
      const res = await api.post("/security/scan-model", { model_path: modelPath });
      setScanResult(res.data);
    } catch (e: any) {
      setScanResult({ error: e.response?.data?.detail || e.message, model_path: modelPath });
    } finally { setScanning(false); }
  };

  const runBenchmark = async (type: string) => {
    setBenchmarking(type);
    setBenchmarkResult(null);
    try {
      const res = await api.post("/security/run-benchmark", null, { params: { benchmark_type: type, agent_id: agentId } });
      setBenchmarkResult(res.data);
    } catch (e: any) {
      setBenchmarkResult({ error: e.response?.data?.detail || e.message });
    } finally { setBenchmarking(null); }
  };

  if (!ready || !authenticated) return <DashboardLayout><div className="flex h-[calc(100vh-4rem)] items-center justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div></div></DashboardLayout>;

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2"><Shield className="h-8 w-8 text-primary" />Model Security</h1>
          <p className="text-muted-foreground">Autonomous vulnerability detection, serialization audit &amp; model assurance</p>
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          <Card><CardHeader className="pb-2"><CardTitle className="text-sm">Scans Run</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{scanResult?.total_scans ?? (scanResult ? 1 : (dashboard?.total_scans ?? 0))}</div></CardContent></Card>
          <Card><CardHeader className="pb-2"><CardTitle className="text-sm">Critical Findings</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold text-red-600">{scanResult?.critical ?? 0}</div></CardContent></Card>
          <Card><CardHeader className="pb-2"><CardTitle className="text-sm">High Findings</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold text-orange-600">{scanResult?.high ?? 0}</div></CardContent></Card>
          <Card><CardHeader className="pb-2"><CardTitle className="text-sm">Status</CardTitle></CardHeader><CardContent><Badge variant={scanResult?.scan_status === "completed" ? "default" : "secondary"}>{scanResult?.scan_status || "idle"}</Badge></CardContent></Card>
        </div>

        <Tabs defaultValue="scan" className="space-y-4">
          <TabsList>
            <TabsTrigger value="scan"><FileText className="mr-2 h-4 w-4" />Model Scan</TabsTrigger>
            <TabsTrigger value="benchmark"><Zap className="mr-2 h-4 w-4" />Benchmarks</TabsTrigger>
            <TabsTrigger value="monitoring"><Activity className="mr-2 h-4 w-4" />Monitoring</TabsTrigger>
          </TabsList>

          <TabsContent value="scan">
            <div className="grid gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader><CardTitle>Scan Model for Vulnerabilities</CardTitle></CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2"><Label>Model Path</Label><Input value={modelPath} onChange={e => setModelPath(e.target.value)} placeholder="./models/my-model" /></div>
                  <Button onClick={handleScan} disabled={scanning} className="w-full">{scanning ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Scanning...</> : "Scan Model"}</Button>
                  <p className="text-xs text-muted-foreground">Detects unsafe serialization (pickle, PyTorch, TensorFlow, ONNX) and model pipeline vulnerabilities</p>
                  <pre className="bg-muted p-3 rounded text-xs overflow-auto">{`artef security scan-model ./my-model --output report.json`}</pre>
                </CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle>Scan Result</CardTitle></CardHeader>
                <CardContent>{scanResult ? <pre className="bg-muted p-3 rounded text-xs overflow-auto max-h-96">{JSON.stringify(scanResult, null, 2)}</pre> : <div className="text-center py-8 text-muted-foreground"><Server className="h-12 w-12 mx-auto mb-2 opacity-30" /><p>No scan yet</p></div>}</CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="benchmark">
            <Card>
              <CardHeader><CardTitle>Benchmarks</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Target agent</Label>
                  <Select value={agentId} onValueChange={setAgentId}>
                    <SelectTrigger><SelectValue placeholder={agents.length ? "Select an agent" : "No agents registered"} /></SelectTrigger>
                    <SelectContent>
                      {agents.map((a) => <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {["safety", "jailbreak", "prompt_injection", "pii", "smoke", "regression"].map((b) => (
                    <Button key={b} variant="outline" onClick={() => runBenchmark(b)} disabled={!agentId || benchmarking !== null}>{benchmarking === b ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}{b.replace("_", " ")}</Button>
                  ))}
                </div>
                {benchmarkResult?.error && <p className="text-sm text-red-600">{String(benchmarkResult.error)}</p>}
                {benchmarkResult && !benchmarkResult.error && (
                  <div className="space-y-3">
                    <p className="text-sm text-muted-foreground"><span className="font-medium text-foreground">{benchmarkResult.benchmark_type.replace("_", " ")}</span> on {benchmarkResult.agent} — {benchmarkResult.total} tests</p>
                    <div className="grid grid-cols-4 gap-2 text-center">
                      <div className="rounded border p-2"><div className="text-xl font-bold text-green-600">{benchmarkResult.passed}</div><div className="text-xs text-muted-foreground">Passed</div></div>
                      <div className="rounded border p-2"><div className="text-xl font-bold text-red-600">{benchmarkResult.failed}</div><div className="text-xs text-muted-foreground">Failed</div></div>
                      <div className="rounded border p-2"><div className="text-xl font-bold text-yellow-600">{benchmarkResult.inconclusive}</div><div className="text-xs text-muted-foreground">Inconclusive</div></div>
                      <div className="rounded border p-2"><div className="text-xl font-bold">{Math.round(benchmarkResult.pass_rate * 100)}%</div><div className="text-xs text-muted-foreground">Pass rate</div></div>
                    </div>
                    {benchmarkResult.findings.length > 0 && (
                      <div className="space-y-1">
                        {benchmarkResult.findings.map((f: any) => (
                          <div key={f.test_case_id} className="flex items-start gap-2 rounded border p-2 text-sm">
                            <Badge variant={f.verdict === "FAIL" ? "destructive" : "secondary"}>{f.verdict}</Badge>
                            <div><span className="font-mono">{f.test_case_id}</span> <span className="text-muted-foreground">({f.severity})</span><div className="text-xs text-muted-foreground">{f.detail}</div></div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                {!benchmarkResult && <div className="text-center py-8 text-muted-foreground"><Zap className="h-12 w-12 mx-auto mb-2 opacity-30" /><p>Pick an agent, then a benchmark. Each test in the suite is sent to the agent and checked with the same deterministic matchers as evaluation runs.</p></div>}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="monitoring">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between"><CardTitle>Security Dashboard</CardTitle><Button size="sm" variant="outline" onClick={fetchDashboard}>Refresh</Button></CardHeader>
              <CardContent>{dashboard ? <pre className="bg-muted p-3 rounded text-xs overflow-auto max-h-96">{JSON.stringify(dashboard, null, 2)}</pre> : <div className="text-center py-8 text-muted-foreground"><Activity className="h-12 w-12 mx-auto mb-2 opacity-30" /><p>Monitoring — tracks guardrail hits, auth failures, cost anomalies</p><p className="text-sm">Integrates with Prometheus + Grafana</p></div>}</CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
}