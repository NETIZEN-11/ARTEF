"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/ui/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { Plus, Loader2, AlertTriangle } from "lucide-react";

interface TestSuite {
  id: string;
  name: string;
  version: number;
  description: string | null;
}

interface TargetAgent {
  id: string;
  name: string;
  description: string | null;
  status: string;
}

interface Baseline {
  id: string;
  name: string;
  description: string | null;
  suite_id: string;
  suite_version: number;
}

export default function NewRunPage() {
  const router = useRouter();
  const { ready, authenticated } = useAuthGuard();
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [agents, setAgents] = useState<TargetAgent[]>([]);
  const [baselines, setBaselines] = useState<Baseline[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const [formData, setFormData] = useState({
    suite_id: "",
    target_agent_id: "",
    baseline_id: "",
    suite_version: 1,
  });

  const fetchData = async () => {
    try {
      const [suitesRes, agentsRes] = await Promise.all([
        api.get("/suites"),
        api.get("/agents"),
      ]);
      console.log("Suites response:", suitesRes.data);
      console.log("Agents response:", agentsRes.data);
      
      // Ensure we have arrays
      const suitesData = Array.isArray(suitesRes.data) ? suitesRes.data : [];
      const agentsData = Array.isArray(agentsRes.data) ? agentsRes.data : [];
      
      setSuites(suitesData);
      setAgents(agentsData);
      
      if (suitesData.length === 0) {
        setError("No test suites found. Please create a test suite first.");
      }
      if (agentsData.length === 0) {
        setError("No target agents found. Please create a target agent first.");
      }
    } catch (error: any) {
      console.error("Failed to fetch data:", error);
      setError(error?.response?.data?.detail || "Failed to load test suites and agents. Please try refreshing the page.");
    } finally {
      setLoading(false);
    }
  };

  const fetchBaselines = async (suiteId: string) => {
    try {
      const res = await api.get(`/baselines?suite_id=${suiteId}`);
      console.log("Baselines response:", res.data);
      const baselinesData = Array.isArray(res.data) ? res.data : [];
      setBaselines(baselinesData);
    } catch (error) {
      console.error("Failed to fetch baselines:", error);
      setBaselines([]);
    }
  };

  useEffect(() => {
    if (!ready || !authenticated) return;
    void fetchData();
  }, [ready, authenticated]);

  useEffect(() => {
    if (formData.suite_id) {
      fetchBaselines(formData.suite_id);
    } else {
      setBaselines([]);
      setFormData((prev) => ({ ...prev, baseline_id: "" }));
    }
  }, [formData.suite_id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.suite_id || !formData.target_agent_id) {
      setError("Please select a test suite and target agent");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      // Only include baseline_id if it's not empty
      const payload: any = {
        suite_id: formData.suite_id,
        target_agent_id: formData.target_agent_id,
        suite_version: formData.suite_version,
      };
      
      // Only add baseline_id if it's a valid UUID (not empty string)
      if (formData.baseline_id && formData.baseline_id.trim() !== "") {
        payload.baseline_id = formData.baseline_id;
      }
      
      const res = await api.post("/runs", payload);
      router.push(`/runs/${res.data.id}`);
    } catch (err: any) {
      console.error("Failed to create run:", err);
      
      // Handle Pydantic validation errors
      if (err.response?.status === 422 && err.response?.data?.detail) {
        const detail = err.response.data.detail;
        
        // Check if it's an array of validation errors (Pydantic format)
        if (Array.isArray(detail)) {
          const errorMessages = detail.map((error: any) => {
            const field = error.loc?.[error.loc.length - 1] || 'unknown';
            return `${field}: ${error.msg}`;
          }).join(', ');
          setError(`Validation error: ${errorMessages}`);
        } else if (typeof detail === 'string') {
          setError(detail);
        } else {
          setError("Validation failed. Please check your inputs.");
        }
      } else {
        setError(err.response?.data?.detail || err.message || "Failed to create evaluation run");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleChange = (field: string, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  if (!ready || !authenticated) {
    return (
      <DashboardLayout>
        <div className="flex h-[calc(100vh-4rem)] items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">New Evaluation Run</h1>
            <p className="text-muted-foreground">Configure and start a new evaluation run</p>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Run Configuration</CardTitle>
            <CardDescription>Select the test suite, target agent, and optional baseline for regression detection</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="suite_id">Test Suite</Label>
                  <Select
                    value={formData.suite_id}
                    onValueChange={(value) => handleChange("suite_id", value)}
                    disabled={submitting}
                  >
                    <SelectTrigger><SelectValue placeholder="Select a test suite" /></SelectTrigger>
                    <SelectContent>
                      {suites.map((suite) => (
                        <SelectItem key={suite.id} value={suite.id}>
                          {suite.name} (v{suite.version})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="suite_version">Suite Version</Label>
                  <Select
                    value={formData.suite_version.toString()}
                    onValueChange={(value) => handleChange("suite_version", parseInt(value))}
                    disabled={submitting || !formData.suite_id}
                  >
                    <SelectTrigger><SelectValue placeholder="Select version" /></SelectTrigger>
                    <SelectContent>
                      {formData.suite_id && suites.find((s) => s.id === formData.suite_id) ? (
                        Array.from(
                          { length: suites.find((s) => s.id === formData.suite_id)!.version },
                          (_, i) => (
                            <SelectItem key={i + 1} value={String(i + 1)}>
                              v{i + 1}
                            </SelectItem>
                          )
                        )
                      ) : (
                        <SelectItem value="1" disabled>
                          Select a suite first
                        </SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="target_agent_id">Target Agent</Label>
                  <Select
                    value={formData.target_agent_id}
                    onValueChange={(value) => handleChange("target_agent_id", value)}
                    disabled={submitting}
                  >
                    <SelectTrigger><SelectValue placeholder="Select a target agent" /></SelectTrigger>
                    <SelectContent>
                      {agents.map((agent) => (
                        <SelectItem key={agent.id} value={agent.id}>
                          {agent.name} ({agent.status})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="baseline_id">Baseline (Optional)</Label>
                  <Select
                    value={formData.baseline_id}
                    onValueChange={(value) => handleChange("baseline_id", value)}
                    disabled={submitting || !formData.suite_id}
                  >
                    <SelectTrigger><SelectValue placeholder="Select a baseline (optional)" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">No baseline</SelectItem>
                      {baselines.map((baseline) => (
                        <SelectItem key={baseline.id} value={baseline.id}>
                          {baseline.name} (v{baseline.suite_version})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button type="button" variant="outline" onClick={() => router.back()} disabled={submitting}>
                  Cancel
                </Button>
                <Button type="submit" disabled={submitting}>
                  {submitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Plus className="mr-2 h-4 w-4" />
                      Create Run
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}