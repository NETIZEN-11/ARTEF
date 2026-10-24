"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, handleApiError } from "@/lib/api";
import { getSeverityColor } from "@/lib/utils";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { useParams, useRouter } from "next/navigation";
import { Plus, Edit, Trash2, AlertTriangle, Upload } from "lucide-react";

interface TestCase {
  id: string;
  test_case_id: string;
  category: string;
  severity: string;
  input: string;
  expected_behavior: Record<string, unknown>;
  metadata: Record<string, unknown>;
  is_active: boolean;
  version: number;
}

interface TestSuite {
  id: string;
  name: string;
  description: string | null;
  version: number;
  schema_version: string;
  is_active: boolean;
  test_cases: TestCase[];
  created_at: string;
  updated_at: string;
}

const LoadingScreen = () => (
  <div className="flex h-screen items-center justify-center">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
  </div>
);

const NotAuthenticated = () => (
  <div className="flex h-screen items-center justify-center">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
  </div>
);

const SuiteNotFound = ({ router }: { router: ReturnType<typeof useRouter> }) => (
  <div className="p-6 text-center">
    <h2 className="text-xl font-medium">Suite not found</h2>
    <Button variant="outline" onClick={() => router.push("/suites")} className="mt-4">
      Go Back
    </Button>
  </div>
);

interface MainContentProps {
  suite: TestSuite | null;
  router: ReturnType<typeof useRouter>;
  handleCreateVersion: () => Promise<void>;
  showCreateCaseDialog: boolean;
  setShowCreateCaseDialog: (v: boolean) => void;
  showImportDialog: boolean;
  setShowImportDialog: (v: boolean) => void;
  importFormat: "yaml" | "json";
  setImportFormat: (v: "yaml" | "json") => void;
  importContent: string;
  setImportContent: (v: string) => void;
  newCase: {
    test_case_id: string;
    category: string;
    severity: string;
    input: string;
    expected_behavior_type: string;
    expected_behavior_matcher: Record<string, unknown>;
    metadata: Record<string, unknown>;
  };
  setNewCase: React.Dispatch<React.SetStateAction<{
    test_case_id: string;
    category: string;
    severity: string;
    input: string;
    expected_behavior_type: string;
    expected_behavior_matcher: Record<string, unknown>;
    metadata: Record<string, unknown>;
  }>>;
  handleCreateCase: () => Promise<void>;
  handleImport: () => Promise<void>;
  editingCase: TestCase | null;
  setEditingCase: React.Dispatch<React.SetStateAction<TestCase | null>>;
  handleUpdateCase: () => Promise<void>;
  handleDeleteCase: (caseId: string) => Promise<void>;
  actionError: string | null;
  getSeverityColor: (severity: string) => string;
}

const MainContent = ({
  suite,
  handleCreateVersion,
  showCreateCaseDialog,
  setShowCreateCaseDialog,
  showImportDialog,
  setShowImportDialog,
  importFormat,
  setImportFormat,
  importContent,
  setImportContent,
  newCase,
  setNewCase,
  handleCreateCase,
  handleImport,
  editingCase,
  setEditingCase,
  handleUpdateCase,
  handleDeleteCase,
  actionError,
  getSeverityColor,
}: MainContentProps) => (
  !suite ? null : (
    <div className="p-6 space-y-6">
      {actionError && (
        <p className="flex items-center gap-1.5 text-sm text-destructive">
          <AlertTriangle className="h-3.5 w-3.5" /> {actionError}
        </p>
      )}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">{suite.name}</h1>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant="secondary">v{suite.version}</Badge>
            <Badge variant={suite.is_active ? "default" : "secondary"}>
              {suite.is_active ? "Active" : "Inactive"}
            </Badge>
            <span className="text-sm text-muted-foreground">Schema: {suite.schema_version}</span>
          </div>
          {suite.description && (
            <p className="text-muted-foreground mt-2">{suite.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleCreateVersion}>
            <Plus className="mr-2 h-4 w-4" /> New Version
          </Button>
          <Dialog open={showCreateCaseDialog} onOpenChange={setShowCreateCaseDialog}>
            <DialogTrigger asChild>
              <Button><Plus className="mr-2 h-4 w-4" /> Add Test Case</Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Add Test Case</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label htmlFor="test_case_id">Test Case ID</Label>
                    <Input
                      id="test_case_id"
                      value={newCase.test_case_id}
                      onChange={(e) => setNewCase({...newCase, test_case_id: e.target.value})}
                      placeholder="e.g., SAFETY_001"
                    />
                  </div>
                  <div>
                    <Label htmlFor="category">Category</Label>
                    <Select value={newCase.category} onValueChange={(v) => setNewCase({...newCase, category: v})}>
                      <SelectTrigger><SelectValue placeholder="Select category" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="smoke">Smoke</SelectItem>
                        <SelectItem value="safety">Safety</SelectItem>
                        <SelectItem value="jailbreak">Jailbreak</SelectItem>
                        <SelectItem value="prompt_injection">Prompt Injection</SelectItem>
                        <SelectItem value="pii">PII</SelectItem>
                        <SelectItem value="policy">Policy</SelectItem>
                        <SelectItem value="refusal">Refusal</SelectItem>
                        <SelectItem value="tool_use">Tool Use</SelectItem>
                        <SelectItem value="hallucination">Hallucination</SelectItem>
                        <SelectItem value="bias">Bias</SelectItem>
                        <SelectItem value="adversarial">Adversarial</SelectItem>
                        <SelectItem value="custom">Custom</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="severity">Severity</Label>
                    <Select value={newCase.severity} onValueChange={(v) => setNewCase({...newCase, severity: v})}>
                      <SelectTrigger><SelectValue placeholder="Select severity" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="critical">Critical</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="low">Low</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="expected_behavior_type">Expected Behavior Type</Label>
                    <Select value={newCase.expected_behavior_type} onValueChange={(v) => setNewCase({...newCase, expected_behavior_type: v})}>
                      <SelectTrigger><SelectValue placeholder="Select type" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="exact_match">Exact Match</SelectItem>
                        <SelectItem value="regex_match">Regex Match</SelectItem>
                        <SelectItem value="keyword_match">Keyword Match</SelectItem>
                        <SelectItem value="refusal">Refusal</SelectItem>
                        <SelectItem value="structured_output">Structured Output</SelectItem>
                        <SelectItem value="llm_rubric">LLM Rubric</SelectItem>
                        <SelectItem value="custom">Custom</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div>
                  <Label htmlFor="input">Input</Label>
                  <Textarea
                    id="input"
                    value={newCase.input}
                    onChange={(e) => setNewCase({...newCase, input: e.target.value})}
                    placeholder="Enter the test input..."
                    rows={3}
                  />
                </div>
                <div>
                  <Label>Expected Behavior Matcher Config (JSON)</Label>
                  <Textarea
                    value={JSON.stringify(newCase.expected_behavior_matcher, null, 2)}
                    onChange={(e) => {
                      try {
                        setNewCase({...newCase, expected_behavior_matcher: JSON.parse(e.target.value)});
                      } catch {}
                    }}
                    placeholder='{"keywords": ["hello", "hi"], "case_sensitive": false}'
                    rows={4}
                    className="font-mono text-sm"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowCreateCaseDialog(false)}>Cancel</Button>
                <Button onClick={handleCreateCase}>Create</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <Dialog open={showImportDialog} onOpenChange={setShowImportDialog}>
            <DialogTrigger asChild>
              <Button variant="outline"><Upload className="mr-2 h-4 w-4" /> Import</Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Import Test Suite</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div>
                  <Label>Format</Label>
                  <Select value={importFormat} onValueChange={(v) => setImportFormat(v as "yaml" | "json")}>
                    <SelectTrigger><SelectValue placeholder="Select format" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="yaml">YAML</SelectItem>
                      <SelectItem value="json">JSON</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="importContent">Content</Label>
                  <Textarea
                    id="importContent"
                    value={importContent}
                    onChange={(e) => setImportContent(e.target.value)}
                    placeholder="Paste YAML or JSON content here..."
                    className="min-h-[300px] font-mono text-sm"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowImportDialog(false)}>Cancel</Button>
                <Button onClick={handleImport}>Import</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Test Cases ({suite?.test_cases.length ?? 0})</CardTitle>
        </CardHeader>
        <CardContent>
          {suite?.test_cases.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-muted-foreground">No test cases yet. Click &#34;Add Test Case&#34; to create one.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Test Case ID</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Input</TableHead>
                    <TableHead>Expected Behavior</TableHead>
                    <TableHead>Version</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-24">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {suite?.test_cases.map((tc) => (
                    <TableRow key={tc.id}>
                      <TableCell className="font-mono text-sm">{tc.test_case_id}</TableCell>
                      <TableCell><Badge variant="secondary">{tc.category}</Badge></TableCell>
                      <TableCell><Badge className={getSeverityColor(tc.severity)}>{tc.severity}</Badge></TableCell>
                      <TableCell className="max-w-xs truncate">{tc.input.slice(0, 100)}...</TableCell>
                      <TableCell className="font-mono text-sm max-w-xs truncate">
                        {String((tc.expected_behavior as Record<string, unknown>)?.type) || "N/A"}
                      </TableCell>
                      <TableCell>v{tc.version}</TableCell>
                      <TableCell>
                        <Badge variant={tc.is_active ? "default" : "secondary"}>
                          {tc.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="icon" onClick={() => setEditingCase(tc)}>
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => handleDeleteCase(tc.id)}>
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {editingCase && (
        <Dialog open={true} onOpenChange={(open) => !open && setEditingCase(null)}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Edit Test Case: {editingCase.test_case_id}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label htmlFor="edit_test_case_id">Test Case ID</Label>
                  <Input
                    id="edit_test_case_id"
                    value={editingCase.test_case_id}
                    onChange={(e) => setEditingCase({...editingCase, test_case_id: e.target.value})}
                  />
                </div>
                <div>
                  <Label htmlFor="edit_category">Category</Label>
                  <Select value={editingCase.category} onValueChange={(v) => setEditingCase({...editingCase!, category: v})}>
                    <SelectTrigger><SelectValue placeholder="Select category" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="smoke">Smoke</SelectItem>
                      <SelectItem value="safety">Safety</SelectItem>
                      <SelectItem value="jailbreak">Jailbreak</SelectItem>
                      <SelectItem value="prompt_injection">Prompt Injection</SelectItem>
                      <SelectItem value="pii">PII</SelectItem>
                      <SelectItem value="policy">Policy</SelectItem>
                      <SelectItem value="refusal">Refusal</SelectItem>
                      <SelectItem value="tool_use">Tool Use</SelectItem>
                      <SelectItem value="hallucination">Hallucination</SelectItem>
                      <SelectItem value="bias">Bias</SelectItem>
                      <SelectItem value="adversarial">Adversarial</SelectItem>
                      <SelectItem value="custom">Custom</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="edit_severity">Severity</Label>
                  <Select value={editingCase.severity} onValueChange={(v) => setEditingCase({...editingCase!, severity: v})}>
                    <SelectTrigger><SelectValue placeholder="Select severity" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="critical">Critical</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="low">Low</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="edit_version">Version</Label>
                  <Input
                    id="edit_version"
                    type="number"
                    value={editingCase.version}
                    onChange={(e) => setEditingCase({...editingCase!, version: parseInt(e.target.value)})}
                  />
                </div>
              </div>
              <div>
                <Label htmlFor="edit_input">Input</Label>
                <Textarea
                  id="edit_input"
                  value={editingCase.input}
                  onChange={(e) => setEditingCase({...editingCase!, input: e.target.value})}
                  rows={3}
                />
              </div>
              <div>
                <Label>Expected Behavior Matcher Config (JSON)</Label>
                <Textarea
                  value={JSON.stringify(editingCase.expected_behavior, null, 2)}
                  onChange={(e) => {
                    try {
                      setEditingCase({...editingCase!, expected_behavior: JSON.parse(e.target.value)});
                    } catch {}
                  }}
                  rows={4}
                  className="font-mono text-sm"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setEditingCase(null)}>Cancel</Button>
              <Button onClick={handleUpdateCase}>Save</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
);

export default function SuiteDetailPage() {
  const router = useRouter();
  const params = useParams();
  const suiteId = params.id as string;
  const { ready, authenticated } = useAuthGuard();
  const [suite, setSuite] = useState<TestSuite | null>(null);
  const [showCreateCaseDialog, setShowCreateCaseDialog] = useState(false);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [importFormat, setImportFormat] = useState<"yaml" | "json">("yaml");
  const [importContent, setImportContent] = useState("");
  const [editingCase, setEditingCase] = useState<TestCase | null>(null);
  const [newCase, setNewCase] = useState({
    test_case_id: "",
    category: "",
    severity: "medium",
    input: "",
    expected_behavior_type: "exact_match",
    expected_behavior_matcher: {},
    metadata: {},
  });

  const fetchSuite = useCallback(async () => {
    try {
      const response = await api.get(`/suites/${suiteId}`);
      setSuite(response.data);
    } catch (error) {
      console.error("Failed to fetch suite:", error);
    }
  }, [suiteId]);

  useEffect(() => {
    if (!ready || !authenticated) return;
    void fetchSuite();
  }, [ready, authenticated, fetchSuite]);

  const handleCreateVersion = async () => {
    setActionError(null);
    try {
      // The endpoint takes the full suite definition; the current suite
      // contents are replayed so the new version is a snapshot of them.
      await api.post(`/suites/${suiteId}/versions`, {
        name: suite?.name ?? "",
        description: suite?.description ?? "",
        test_cases: (suite?.test_cases ?? []).map((tc) => ({
          test_case_id: tc.test_case_id,
          category: tc.category,
          severity: tc.severity,
          input: tc.input,
          expected_behavior: tc.expected_behavior ?? {},
          metadata: tc.metadata ?? {},
        })),
      });
      await fetchSuite();
    } catch (error) {
      setActionError(handleApiError(error));
    }
  };

  const handleCreateCase = async () => {
    setActionError(null);
    try {
      await api.post(`/suites/${suiteId}/test-cases`, newCase);
      setShowCreateCaseDialog(false);
      setNewCase({
        test_case_id: "",
        category: "",
        severity: "medium",
        input: "",
        expected_behavior_type: "exact_match",
        expected_behavior_matcher: {},
        metadata: {},
      });
      await fetchSuite();
    } catch (error) {
      setActionError(handleApiError(error));
    }
  };

  const handleUpdateCase = async () => {
    if (!editingCase) return;
    setActionError(null);
    try {
      // The API stores the behaviour as three fields; the UI receives it as a
      // single `expected_behavior` object, so it is split back here.
      const behavior = editingCase.expected_behavior ?? {};
      await api.put(`/suites/${suiteId}/test-cases/${editingCase.id}`, {
        test_case_id: editingCase.test_case_id,
        category: editingCase.category,
        severity: editingCase.severity,
        input: editingCase.input,
        expected_behavior_type: (behavior.type as string) ?? "",
        expected_behavior_matcher: (behavior.matcher as Record<string, unknown>) ?? {},
        metadata: editingCase.metadata,
        is_active: editingCase.is_active,
      });
      setEditingCase(null);
      await fetchSuite();
    } catch (error) {
      setActionError(handleApiError(error));
    }
  };

  const handleDeleteCase = async (caseId: string) => {
    if (!confirm("Are you sure you want to delete this test case?")) return;
    setActionError(null);
    try {
      await api.delete(`/suites/${suiteId}/test-cases/${caseId}`);
      await fetchSuite();
    } catch (error) {
      setActionError(handleApiError(error));
    }
  };

  const handleImport = async () => {
    setActionError(null);
    try {
      await api.post(`/suites/${suiteId}/import`, { content: importContent, format: importFormat });
      setShowImportDialog(false);
      setImportContent("");
      await fetchSuite();
    } catch (error) {
      setActionError(handleApiError(error));
    }
  };

  if (!ready || !authenticated) {
    return <LoadingScreen />;
  }

  if (!suite) {
    return <SuiteNotFound router={router} />;
  }

  return <MainContent
    suite={suite}
    router={router}
    handleCreateVersion={handleCreateVersion}
    showCreateCaseDialog={showCreateCaseDialog}
    setShowCreateCaseDialog={setShowCreateCaseDialog}
    showImportDialog={showImportDialog}
    setShowImportDialog={setShowImportDialog}
    importFormat={importFormat}
    setImportFormat={setImportFormat}
    importContent={importContent}
    setImportContent={setImportContent}
    newCase={newCase}
    setNewCase={setNewCase}
    handleCreateCase={handleCreateCase}
    handleImport={handleImport}
    editingCase={editingCase}
    setEditingCase={setEditingCase}
    handleUpdateCase={handleUpdateCase}
    handleDeleteCase={handleDeleteCase}
    actionError={actionError}
    getSeverityColor={getSeverityColor}
  />;
}
