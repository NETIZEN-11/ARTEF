"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/ui/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { useAuth, getAccessToken } from "@/lib/auth";
import {
  Plus, Edit, Trash2, Wifi, WifiOff, RefreshCw, AlertTriangle,
  Search, CheckCircle2, XCircle, Clock, Shield, ShieldOff, Activity,
  Globe, Zap, Settings2, ChevronDown, ChevronRight, Copy,
  Filter, Server, FlaskConical,
} from "lucide-react";

type JsonObject = Record<string, unknown>;

interface TargetAgent {
  id: string;
  name: string;
  description: string | null;
  endpoint_url: string;
  auth_config: JsonObject;
  request_template: JsonObject | null;
  response_extraction: JsonObject | null;
  timeout_seconds: number;
  max_retries: number;
  allowed: boolean;
  status: string;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

interface AgentFormValues {
  name: string;
  description: string;
  endpoint_url: string;
  auth_config: JsonObject;
  request_template: JsonObject;
  response_extraction: JsonObject;
  timeout_seconds: number;
  max_retries: number;
  allowed: boolean;
}

const defaultNewAgent: AgentFormValues = {
  name: "",
  description: "",
  endpoint_url: "",
  auth_config: {},
  request_template: { input: "{input}" },
  response_extraction: { response: "response" },
  timeout_seconds: 30,
  max_retries: 3,
  allowed: true,
};

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; className: string; dot: string }> = {
    active: { label: "Active", className: "bg-emerald-500/15 text-emerald-500 border-emerald-500/30", dot: "bg-emerald-500" },
    testing: { label: "Testing", className: "bg-amber-500/15 text-amber-500 border-amber-500/30", dot: "bg-amber-500" },
    inactive: { label: "Inactive", className: "bg-slate-500/15 text-slate-400 border-slate-500/30", dot: "bg-slate-400" },
    error: { label: "Error", className: "bg-red-500/15 text-red-400 border-red-500/30", dot: "bg-red-400" },
  };
  const cfg = map[status] ?? map["inactive"];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${cfg.className}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot} animate-pulse`} />
      {cfg.label}
    </span>
  );
}

function StatCard({
  label, value, icon: Icon, color, sub,
}: {
  label: string; value: string | number; icon: React.ElementType; color: string; sub?: string;
}) {
  return (
    <div className="relative overflow-hidden rounded-xl border border-border bg-card p-5 flex gap-4 items-start transition-all duration-200 hover:shadow-md hover:border-primary/30 group">
      <div className={`flex-shrink-0 w-11 h-11 rounded-lg flex items-center justify-center ${color} transition-transform duration-200 group-hover:scale-105`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="min-w-0">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-2xl font-bold tracking-tight">{value}</p>
        {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

function AgentFormFields({
  values, onChange,
}: {
  values: AgentFormValues;
  onChange: (v: Partial<AgentFormValues>) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="f-name">Name <span className="text-destructive">*</span></Label>
          <Input id="f-name" value={values.name} onChange={(e) => onChange({ name: e.target.value })} placeholder="My Production Agent" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="f-endpoint">Endpoint URL <span className="text-destructive">*</span></Label>
          <Input id="f-endpoint" value={values.endpoint_url} onChange={(e) => onChange({ endpoint_url: e.target.value })} placeholder="https://api.internal.example/v1/chat" />
        </div>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="f-desc">Description</Label>
        <Textarea id="f-desc" value={values.description} onChange={(e) => onChange({ description: e.target.value })} placeholder="What does this agent do?" rows={2} className="resize-none" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="f-timeout">Timeout (seconds)</Label>
          <Input id="f-timeout" type="number" min={1} max={300} value={values.timeout_seconds} onChange={(e) => onChange({ timeout_seconds: parseInt(e.target.value) || 30 })} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="f-retries">Max Retries</Label>
          <Input id="f-retries" type="number" min={0} max={10} value={values.max_retries} onChange={(e) => onChange({ max_retries: parseInt(e.target.value) || 0 })} />
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="f-req-tmpl">Request Template (JSON)</Label>
          <Textarea id="f-req-tmpl" value={JSON.stringify(values.request_template, null, 2)} onChange={(e) => { try { onChange({ request_template: JSON.parse(e.target.value) }); } catch {} }} rows={4} className="font-mono text-xs resize-none" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="f-res-ext">Response Extraction (JSON)</Label>
          <Textarea id="f-res-ext" value={JSON.stringify(values.response_extraction, null, 2)} onChange={(e) => { try { onChange({ response_extraction: JSON.parse(e.target.value) }); } catch {} }} rows={4} className="font-mono text-xs resize-none" />
        </div>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="f-auth">Auth Config (JSON)</Label>
        <Textarea id="f-auth" value={JSON.stringify(values.auth_config, null, 2)} onChange={(e) => { try { onChange({ auth_config: JSON.parse(e.target.value) }); } catch {} }} rows={3} className="font-mono text-xs resize-none" placeholder='{"type": "bearer", "token": "..."}' />
      </div>
      <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50 border border-border">
        <input type="checkbox" id="f-allowed" checked={values.allowed} onChange={(e) => onChange({ allowed: e.target.checked })} className="h-4 w-4 rounded accent-primary cursor-pointer" />
        <div>
          <Label htmlFor="f-allowed" className="cursor-pointer font-medium">Enable for Evaluations</Label>
          <p className="text-xs text-muted-foreground">When enabled, this agent can be targeted in red-team runs</p>
        </div>
      </div>
    </div>
  );
}

function AgentCard({
  agent, onEdit, onDelete, onTest, testingAgentId, testInput, setTestInput, testResult, testLoading, onRunTest,
}: {
  agent: TargetAgent;
  onEdit: (a: TargetAgent) => void;
  onDelete: (id: string) => void;
  onTest: (a: TargetAgent) => void;
  testingAgentId: string | null;
  testInput: string;
  setTestInput: (v: string) => void;
  testResult: string | null;
  testLoading: boolean;
  onRunTest: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const isTesting = testingAgentId === agent.id;
  const copyToClipboard = (text: string) => navigator.clipboard.writeText(text);

  return (
    <div className={`rounded-xl border bg-card overflow-hidden transition-all duration-200 hover:shadow-md ${!agent.allowed ? "opacity-60" : ""}`}>
      <div className="px-5 py-4 flex items-start gap-4">
        <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center ${agent.allowed ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"}`}>
          <Server className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-base">{agent.name}</h3>
            <StatusBadge status={agent.status} />
            {!agent.allowed && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-red-500/10 text-red-400 border border-red-500/20">
                <ShieldOff className="w-3 h-3" /> Blocked
              </span>
            )}
          </div>
          {agent.description && <p className="text-sm text-muted-foreground mt-0.5">{agent.description}</p>}
          <div className="flex items-center gap-1.5 mt-1.5 group/url">
            <Globe className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
            <span className="text-xs font-mono text-muted-foreground truncate">{agent.endpoint_url}</span>
            <button onClick={() => copyToClipboard(agent.endpoint_url)} className="opacity-0 group-hover/url:opacity-100 transition-opacity" title="Copy URL">
              <Copy className="w-3 h-3 text-muted-foreground hover:text-foreground" />
            </button>
          </div>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => { onTest(agent); setExpanded(true); }} title="Test Connection">
            <FlaskConical className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onEdit(agent)} title="Edit">
            <Edit className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8 hover:text-destructive hover:bg-destructive/10" onClick={() => onDelete(agent.id)} title="Delete">
            <Trash2 className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setExpanded(!expanded)}>
            {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      <div className="px-5 py-2 bg-muted/40 border-t border-border flex items-center gap-6 text-xs text-muted-foreground flex-wrap">
        <span className="flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" />{agent.timeout_seconds}s timeout</span>
        <span className="flex items-center gap-1.5"><RefreshCw className="w-3.5 h-3.5" />{agent.max_retries} retries</span>
        <span className="flex items-center gap-1.5">
          {agent.allowed ? <Shield className="w-3.5 h-3.5 text-emerald-500" /> : <ShieldOff className="w-3.5 h-3.5 text-red-400" />}
          {agent.allowed ? "Evaluations allowed" : "Evaluations blocked"}
        </span>
        <span className="ml-auto">Updated {formatDate(agent.updated_at)}</span>
      </div>

      {expanded && (
        <div className="border-t border-border">
          <Tabs defaultValue={isTesting ? "test" : "config"} className="w-full">
            <div className="px-5 pt-3">
              <TabsList className="h-8">
                <TabsTrigger value="config" className="text-xs h-7"><Settings2 className="w-3.5 h-3.5 mr-1.5" />Configuration</TabsTrigger>
                <TabsTrigger value="test" className="text-xs h-7"><FlaskConical className="w-3.5 h-3.5 mr-1.5" />Test Connection</TabsTrigger>
              </TabsList>
            </div>
            <TabsContent value="config" className="px-5 pb-5 pt-3 space-y-4">
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Request Template</p>
                  <pre className="bg-muted/60 p-3 rounded-lg text-xs font-mono overflow-auto max-h-40 border border-border">{JSON.stringify(agent.request_template, null, 2) || "null"}</pre>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Response Extraction</p>
                  <pre className="bg-muted/60 p-3 rounded-lg text-xs font-mono overflow-auto max-h-40 border border-border">{JSON.stringify(agent.response_extraction, null, 2) || "null"}</pre>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Auth Config</p>
                  <pre className="bg-muted/60 p-3 rounded-lg text-xs font-mono overflow-auto max-h-40 border border-border">
                    {Object.keys(agent.auth_config || {}).length === 0 ? "// No auth configured" : JSON.stringify(agent.auth_config, null, 2)}
                  </pre>
                </div>
              </div>
              <div className="flex items-center gap-6 text-sm pt-1 border-t border-border flex-wrap">
                <div>
                  <span className="text-muted-foreground">Agent ID:</span>
                  <code className="ml-1.5 text-xs bg-muted px-1.5 py-0.5 rounded font-mono">{agent.id.slice(0, 8)}…</code>
                  <button onClick={() => copyToClipboard(agent.id)} className="ml-1"><Copy className="w-3 h-3 inline text-muted-foreground hover:text-foreground" /></button>
                </div>
                <div><span className="text-muted-foreground">Created:</span><span className="ml-1.5">{formatDate(agent.created_at)}</span></div>
                {agent.created_by && <div><span className="text-muted-foreground">By:</span><span className="ml-1.5">{agent.created_by}</span></div>}
              </div>
            </TabsContent>
            <TabsContent value="test" className="px-5 pb-5 pt-3 space-y-3">
              <div>
                <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Test Input</Label>
                <Textarea
                  value={isTesting ? testInput : ""}
                  onChange={(e) => setTestInput(e.target.value)}
                  onFocus={() => onTest(agent)}
                  placeholder="Enter a test prompt to send to this agent…"
                  rows={3}
                  className="mt-1.5 font-mono text-sm resize-none"
                />
              </div>
              <div className="flex items-center gap-3">
                <Button size="sm" onClick={() => { onTest(agent); onRunTest(); }} disabled={testLoading && isTesting} className="gap-2">
                  {testLoading && isTesting ? <><RefreshCw className="w-3.5 h-3.5 animate-spin" />Testing…</> : <><Zap className="w-3.5 h-3.5" />Run Test</>}
                </Button>
                <span className="text-xs text-muted-foreground">Sends a live request to the agent endpoint</span>
              </div>
              {isTesting && testResult && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1.5">
                    {testResult.startsWith("Error")
                      ? <span className="text-red-400 flex items-center gap-1"><XCircle className="w-3.5 h-3.5" />Error Response</span>
                      : <span className="text-emerald-500 flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" />Success Response</span>}
                  </p>
                  <pre className={`p-3 rounded-lg text-xs font-mono overflow-auto max-h-64 border ${testResult.startsWith("Error") ? "bg-red-500/5 border-red-500/20 text-red-300" : "bg-emerald-500/5 border-emerald-500/20 text-emerald-200"}`}>
                    {testResult}
                  </pre>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      )}
    </div>
  );
}

export default function AgentsPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [agents, setAgents] = useState<TargetAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingAgent, setEditingAgent] = useState<TargetAgent | null>(null);
  const [testingAgentId, setTestingAgentId] = useState<string | null>(null);
  const [testInput, setTestInput] = useState("Hello, how are you?");
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testLoading, setTestLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [newAgent, setNewAgent] = useState(defaultNewAgent);
  const [creating, setCreating] = useState(false);
  const [updating, setUpdating] = useState(false);

  const fetchAgents = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const res = await api.get("/agents");
      setAgents(res.data);
    } catch {
      setError("Failed to load agents. Please check your connection.");
      setAgents([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const token = getAccessToken();
    if (token) { fetchAgents(); return; }
    if (!isLoading && !isAuthenticated) router.replace("/login");
    else if (!isLoading && isAuthenticated) fetchAgents();
  }, [isAuthenticated, isLoading, fetchAgents, router]);

  useEffect(() => {
    if (!isAuthenticated || loading) return;
    const interval = setInterval(() => fetchAgents(true), 30000);
    return () => clearInterval(interval);
  }, [isAuthenticated, loading, fetchAgents]);

  const handleCreateAgent = async () => {
    if (!newAgent.name.trim() || !newAgent.endpoint_url.trim()) return;
    setCreating(true);
    try {
      await api.post("/agents", newAgent);
      setShowCreateDialog(false);
      setNewAgent(defaultNewAgent);
      fetchAgents();
    } catch {} finally { setCreating(false); }
  };

  const handleUpdateAgent = async () => {
    if (!editingAgent) return;
    setUpdating(true);
    try {
      await api.put(`/agents/${editingAgent.id}`, editingAgent);
      setEditingAgent(null);
      fetchAgents();
    } catch {} finally { setUpdating(false); }
  };

  const handleDeleteAgent = async (agentId: string) => {
    if (!confirm("Are you sure you want to delete this agent? This action cannot be undone.")) return;
    try { await api.delete(`/agents/${agentId}`); fetchAgents(); } catch {}
  };

  const handleTestAgent = (agent: TargetAgent) => {
    if (testingAgentId !== agent.id) { setTestingAgentId(agent.id); setTestResult(null); }
  };

  const handleRunTest = async () => {
    if (!testingAgentId || !testInput.trim()) return;
    setTestLoading(true);
    setTestResult(null);
    try {
      const res = await api.post(`/agents/${testingAgentId}/test`, { input: testInput });
      setTestResult(JSON.stringify(res.data, null, 2));
    } catch (error: unknown) {
      const err = error as { response?: { data?: { message?: string; detail?: string } } };
      setTestResult(`Error: ${err.response?.data?.message || err.response?.data?.detail || "Unknown error"}`);
    } finally { setTestLoading(false); }
  };

  const filteredAgents = agents.filter((agent) => {
    const matchesSearch =
      agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (agent.description?.toLowerCase().includes(searchQuery.toLowerCase()) ?? false) ||
      agent.endpoint_url.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === "all" ||
      (statusFilter === "active" && agent.status === "active") ||
      (statusFilter === "inactive" && agent.status !== "active") ||
      (statusFilter === "allowed" && agent.allowed) ||
      (statusFilter === "blocked" && !agent.allowed);
    return matchesSearch && matchesStatus;
  });

  const totalAgents = agents.length;
  const activeAgents = agents.filter((a) => a.status === "active").length;
  const allowedAgents = agents.filter((a) => a.allowed).length;
  const blockedAgents = agents.filter((a) => !a.allowed).length;

  if (isLoading && !getAccessToken()) {
    return (
      <DashboardLayout>
        <div className="flex h-[calc(100vh-4rem)] items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            <p className="text-sm text-muted-foreground">Loading agents…</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6 pb-8">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 mb-1">
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                <Server className="w-4 h-4 text-primary" />
              </div>
              <h1 className="text-2xl font-bold tracking-tight">Target Agents</h1>
            </div>
            <p className="text-sm text-muted-foreground">Manage AI agents and endpoints for red-team evaluations</p>
            {error && (
              <p className="mt-2 text-sm text-destructive flex items-center gap-1.5">
                <AlertTriangle className="h-3.5 w-3.5" /> {error}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => fetchAgents(true)} disabled={refreshing} className="gap-2">
              <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
              <DialogTrigger asChild>
                <Button size="sm" className="gap-2"><Plus className="h-4 w-4" />New Agent</Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2"><Plus className="w-4 h-4" />Create Target Agent</DialogTitle>
                </DialogHeader>
                <div className="py-2">
                  <AgentFormFields values={newAgent} onChange={(v) => setNewAgent((prev) => ({ ...prev, ...v }))} />
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
                  <Button onClick={handleCreateAgent} disabled={creating || !newAgent.name.trim() || !newAgent.endpoint_url.trim()}>
                    {creating ? <><RefreshCw className="w-3.5 h-3.5 mr-2 animate-spin" />Creating…</> : "Create Agent"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        {/* Stats */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Total Agents" value={totalAgents} icon={Server} color="bg-primary/10 text-primary" sub={`${allowedAgents} allowed for evaluation`} />
          <StatCard label="Active" value={activeAgents} icon={Activity} color="bg-emerald-500/10 text-emerald-500" sub={`${((activeAgents / Math.max(totalAgents, 1)) * 100).toFixed(0)}% of total`} />
          <StatCard label="Allowed" value={allowedAgents} icon={Shield} color="bg-blue-500/10 text-blue-500" sub="Enabled for red-team runs" />
          <StatCard label="Blocked" value={blockedAgents} icon={ShieldOff} color="bg-red-500/10 text-red-400" sub="Disabled from evaluations" />
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search agents by name, URL, or description…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 h-9"
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Filter className="w-4 h-4 text-muted-foreground flex-shrink-0" />
            {["all", "active", "inactive", "allowed", "blocked"].map((f) => (
              <Button key={f} variant={statusFilter === f ? "default" : "outline"} size="sm" onClick={() => setStatusFilter(f)} className="h-9 capitalize">
                {f}
              </Button>
            ))}
          </div>
        </div>

        {/* Agent List */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-24 gap-3">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            <p className="text-sm text-muted-foreground">Loading agents…</p>
          </div>
        ) : filteredAgents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center">
              <WifiOff className="w-8 h-8 text-muted-foreground" />
            </div>
            <div className="text-center">
              <h3 className="font-semibold">{searchQuery || statusFilter !== "all" ? "No agents match your filters" : "No agents yet"}</h3>
              <p className="text-sm text-muted-foreground mt-1">
                {searchQuery || statusFilter !== "all" ? "Try clearing your search or filters." : "Create your first target agent to get started with evaluations."}
              </p>
            </div>
            {!searchQuery && statusFilter === "all" && (
              <Button size="sm" onClick={() => setShowCreateDialog(true)} className="gap-2">
                <Plus className="w-4 h-4" />Create First Agent
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Showing <span className="font-medium text-foreground">{filteredAgents.length}</span> of{" "}
              <span className="font-medium text-foreground">{totalAgents}</span> agents
            </p>
            {filteredAgents.map((agent) => (
              <AgentCard
                key={agent.id}
                agent={agent}
                onEdit={setEditingAgent}
                onDelete={handleDeleteAgent}
                onTest={handleTestAgent}
                testingAgentId={testingAgentId}
                testInput={testInput}
                setTestInput={setTestInput}
                testResult={testResult}
                testLoading={testLoading}
                onRunTest={handleRunTest}
              />
            ))}
          </div>
        )}

        {/* Edit Dialog */}
        {editingAgent && (
          <Dialog open={true} onOpenChange={(open) => !open && setEditingAgent(null)}>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2"><Edit className="w-4 h-4" />Edit Agent: {editingAgent.name}</DialogTitle>
              </DialogHeader>
              <div className="py-2">
                <AgentFormFields
                  values={{
                    name: editingAgent.name,
                    description: editingAgent.description || "",
                    endpoint_url: editingAgent.endpoint_url,
                    auth_config: editingAgent.auth_config,
                    request_template: editingAgent.request_template ?? { input: "{input}" },
                    response_extraction: editingAgent.response_extraction ?? { response: "response" },
                    timeout_seconds: editingAgent.timeout_seconds,
                    max_retries: editingAgent.max_retries,
                    allowed: editingAgent.allowed,
                  }}
                  onChange={(v) => setEditingAgent((prev) => prev ? { ...prev, ...v } : prev)}
                />
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setEditingAgent(null)}>Cancel</Button>
                <Button onClick={handleUpdateAgent} disabled={updating}>
                  {updating ? <><RefreshCw className="w-3.5 h-3.5 mr-2 animate-spin" />Saving…</> : "Save Changes"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>
    </DashboardLayout>
  );
}
