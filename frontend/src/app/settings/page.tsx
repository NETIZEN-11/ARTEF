"use client";

import { useEffect, useState, useCallback } from "react";

import { useTheme } from "next-themes";
import { DashboardLayout } from "@/components/ui/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { api, handleApiError } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { User, Shield, Key, Database, Save, Loader2, Edit, Trash2, Plus, AlertTriangle } from "lucide-react";

interface UserInfo {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  last_login: string | null;
  created_at: string;
  roles: string[];
}

interface SystemConfig {
  app_name: string;
  app_version: string;
  environment: string;
  eval_mode: string;
  judge_model: string;
  generator_model: string;
  planner_model: string;
  embedding_model: string;
  cost_per_run_limit: number;
  cost_daily_limit: number;
  retention_days: {
    transcripts: number;
    critical_findings: number;
    reports: number;
    audit_logs: number;
  };
}

interface FeatureFlag {
  id: string;
  name: string;
  description: string | null;
  enabled: boolean;
  rollout_percentage: number;
  target_roles: string[];
  created_at: string;
  updated_at: string;
}

interface AuditLog {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export default function SettingsPage() {
  const { user } = useAuth();
  const { ready, authenticated } = useAuthGuard();
  const { theme, setTheme } = useTheme();
  // The theme is only known in the browser. Until the component has
  // mounted the server and the client would render different markup.
  const [mounted, setMounted] = useState(false);
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [featureFlags, setFeatureFlags] = useState<FeatureFlag[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [systemConfig, setSystemConfig] = useState<SystemConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [emailDraft, setEmailDraft] = useState("");
  const [fullNameDraft, setFullNameDraft] = useState("");
  const [activeTab, setActiveTab] = useState("profile");
  const [showCreateFlagDialog, setShowCreateFlagDialog] = useState(false);
  const [newFlag, setNewFlag] = useState({ name: "", description: "", enabled: false, rollout_percentage: 0, target_roles: [] });
  const [editingFlag, setEditingFlag] = useState<FeatureFlag | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [changingPassword, setChangingPassword] = useState(false);

  const fetchUserInfo = useCallback(async () => {
    try {
      const res = await api.get("/users/me");
      setUserInfo(res.data);
      setEmailDraft(res.data?.email ?? "");
      setFullNameDraft(res.data?.full_name ?? "");
    } catch (error) {
      console.error("Failed to fetch user info:", error);
    }
  }, []);

  const fetchFeatureFlags = useCallback(async () => {
    try {
      const res = await api.get("/settings/feature-flags");
      setFeatureFlags(res.data);
    } catch (error) {
      console.error("Failed to fetch feature flags:", error);
    }
  }, []);

  const fetchAuditLogs = useCallback(async () => {
    try {
      const res = await api.get("/settings/audit-logs?limit=100");
      setAuditLogs(res.data);
    } catch (error) {
      console.error("Failed to fetch audit logs:", error);
    }
  }, []);

  const fetchSystemConfig = useCallback(async () => {
    try {
      const res = await api.get("/settings/config");
      setSystemConfig(res.data);
    } catch (error) {
      console.error("Failed to fetch system config:", error);
    }
  }, []);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!ready || !authenticated) return;
    void fetchUserInfo();
    void fetchFeatureFlags();
    void fetchAuditLogs();
    void fetchSystemConfig();
  }, [ready, authenticated, fetchUserInfo, fetchFeatureFlags, fetchAuditLogs, fetchSystemConfig]);

  /**
   * Change the signed-in user's password.
   *
   * The button previously had no handler, so the form could never be
   * submitted and the value was silently discarded.
   */
  const handleChangePassword = async () => {
    if (!currentPassword || !newPassword) {
      setPasswordError("Both the current and the new password are required");
      setPasswordMessage(null);
      return;
    }
    setChangingPassword(true);
    setPasswordError(null);
    setPasswordMessage(null);
    try {
      const res = await api.post("/users/me/password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPasswordMessage(res.data?.message ?? "Password updated successfully");
      setCurrentPassword("");
      setNewPassword("");
    } catch (err) {
      setPasswordError(handleApiError(err));
    } finally {
      setChangingPassword(false);
    }
  };

  /**
   * Persist a profile change.
   *
   * Text fields commit on blur rather than on every keystroke: the previous
   * implementation issued one PATCH request per character typed.
   */
  const handleUpdateProfile = async (data: Partial<UserInfo>) => {
    setSaving(true);
    setProfileError(null);
    try {
      await api.patch("/users/me", data);
      setUserInfo(prev => prev ? { ...prev, ...data } : null);
    } catch (err) {
      setProfileError(handleApiError(err));
    } finally {
      setSaving(false);
    }
  };

  const handleProfileBlur = async (field: "email" | "full_name", value: string) => {
    if (!userInfo) return;
    if (userInfo[field] === value) return;
    await handleUpdateProfile({ [field]: value });
  };

  const handleCreateFlag = async () => {
    if (!newFlag.name) return;
    setSaving(true);
    try {
      await api.post("/settings/feature-flags", newFlag);
      setShowCreateFlagDialog(false);
      setNewFlag({ name: "", description: "", enabled: false, rollout_percentage: 0, target_roles: [] });
      fetchFeatureFlags();
    } catch (error) {
      console.error("Failed to create feature flag:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateFlag = async (flag: FeatureFlag) => {
    setSaving(true);
    try {
      await api.put(`/settings/feature-flags/${flag.id}`, flag);
      setEditingFlag(null);
      await fetchFeatureFlags();
    } catch (error) {
      setProfileError(handleApiError(error));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteFlag = async (flagId: string) => {
    if (!confirm("Are you sure you want to delete this feature flag?")) return;
    try {
      await api.delete(`/settings/feature-flags/${flagId}`);
      fetchFeatureFlags();
    } catch (error) {
      console.error("Failed to delete feature flag:", error);
    }
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
            <h1 className="text-3xl font-bold">Settings</h1>
            <p className="text-muted-foreground">Manage your profile and system settings</p>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList>
            <TabsTrigger value="profile"><User className="mr-2 h-4 w-4" /> Profile</TabsTrigger>
            <TabsTrigger value="security"><Shield className="mr-2 h-4 w-4" /> Security</TabsTrigger>
            <TabsTrigger value="features"><Key className="mr-2 h-4 w-4" /> Feature Flags</TabsTrigger>
            <TabsTrigger value="audit"><Database className="mr-2 h-4 w-4" /> Audit Logs</TabsTrigger>
          </TabsList>

          <TabsContent value="profile">
            {profileError && (
              <p className="mb-4 flex items-center gap-1.5 text-sm text-destructive">
                <AlertTriangle className="h-3.5 w-3.5" /> {profileError}
              </p>
            )}
            <div className="grid gap-6 md:grid-cols-3">
              <Card>
                <CardHeader>
                  <CardTitle>Profile Information</CardTitle>
                  <CardDescription>Update your personal information</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      value={emailDraft}
                      onChange={(e) => setEmailDraft(e.target.value)}
                      onBlur={(e) => handleProfileBlur("email", e.target.value)}
                      disabled={!userInfo}
                    />
                  </div>
                  <div>
                    <Label htmlFor="username">Username</Label>
                    <Input
                      id="username"
                      value={userInfo?.username || ""}
                      disabled
                      readOnly
                    />
                  </div>
                  <div>
                    <Label htmlFor="full_name">Full Name</Label>
                    <Input
                      id="full_name"
                      value={fullNameDraft}
                      onChange={(e) => setFullNameDraft(e.target.value)}
                      onBlur={(e) => handleProfileBlur("full_name", e.target.value)}
                      disabled={!userInfo}
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch
                      id="is_active"
                      checked={userInfo?.is_active || false}
                      onCheckedChange={(checked) => handleUpdateProfile({ is_active: checked })}
                    />
                    <Label htmlFor="is_active">Active</Label>
                  </div>
                  {userInfo && (
                    <div className="border-t pt-4 space-y-2">
                      <p className="text-sm text-muted-foreground">Account Details</p>
                      <dl className="grid grid-cols-2 gap-2 text-sm">
                        <dt className="text-muted-foreground">User ID</dt>
                        <dd className="font-mono text-xs">{userInfo.id}</dd>
                        <dt className="text-muted-foreground">Superuser</dt>
                        <dd>{userInfo.is_superuser ? "Yes" : "No"}</dd>
                        <dt className="text-muted-foreground">Last Login</dt>
                        <dd>{userInfo.last_login ? formatDate(userInfo.last_login) : "Never"}</dd>
                        <dt className="text-muted-foreground">Created</dt>
                        <dd>{formatDate(userInfo.created_at)}</dd>
                        <dt className="text-muted-foreground">Roles</dt>
                        <dd>{userInfo.roles.join(", ") || "None"}</dd>
                      </dl>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Security</CardTitle>
                  <CardDescription>Manage authentication settings</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label htmlFor="current_password">Current Password</Label>
                    <Input
                      id="current_password"
                      type="password"
                      placeholder="Enter your current password"
                      autoComplete="current-password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label htmlFor="new_password">New Password</Label>
                    <Input
                      id="new_password"
                      type="password"
                      placeholder="Enter a new password"
                      autoComplete="new-password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                    />
                    <p className="text-sm text-muted-foreground mt-1">
                      At least 12 characters, with mixed case, a digit and a special character.
                    </p>
                  </div>
                  {passwordError && (
                    <p className="flex items-center gap-1.5 text-sm text-destructive">
                      <AlertTriangle className="h-3.5 w-3.5" /> {passwordError}
                    </p>
                  )}
                  {passwordMessage && (
                    <p className="text-sm text-green-600">{passwordMessage}</p>
                  )}
                  <Button onClick={handleChangePassword} disabled={changingPassword}>
                    {changingPassword ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Save className="mr-2 h-4 w-4" />
                    )}
                    Update Password
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Preferences</CardTitle>
                  <CardDescription>Customize your experience</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">Dark Mode</p>
                      <p className="text-sm text-muted-foreground">Use dark theme</p>
                    </div>
                    <Switch
                      id="dark_mode"
                      // next-themes returns undefined during server
                      // rendering and the resolved theme in the browser.
                      // Rendering the switch before the client has mounted
                      // produced a hydration mismatch, so the control is
                      // only rendered once the theme is known.
                      checked={mounted && theme === "dark"}
                      onCheckedChange={(checked) => setTheme(checked ? "dark" : "light")}
                    />
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="security">
            <Card>
              <CardHeader>
                <CardTitle>System Configuration</CardTitle>
                <CardDescription>
                  Read-only view of the effective server configuration. Values are managed
                  through environment variables, not from the browser.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {!systemConfig ? (
                  <p className="text-sm text-muted-foreground">Loading configuration...</p>
                ) : (
                  <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
                    <div>
                      <dt className="text-sm text-muted-foreground">Application</dt>
                      <dd className="text-sm font-medium">
                        {systemConfig.app_name} v{systemConfig.app_version}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm text-muted-foreground">Environment</dt>
                      <dd className="text-sm font-medium">{systemConfig.environment}</dd>
                    </div>
                    <div>
                      <dt className="text-sm text-muted-foreground">Evaluation mode</dt>
                      <dd className="text-sm font-medium">{systemConfig.eval_mode}</dd>
                    </div>
                    <div>
                      <dt className="text-sm text-muted-foreground">Judge model</dt>
                      <dd className="text-sm font-medium font-mono text-xs">
                        {systemConfig.judge_model}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm text-muted-foreground">Generator model</dt>
                      <dd className="text-sm font-medium font-mono text-xs">
                        {systemConfig.generator_model}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm text-muted-foreground">Planner model</dt>
                      <dd className="text-sm font-medium font-mono text-xs">
                        {systemConfig.planner_model}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm text-muted-foreground">Embedding model</dt>
                      <dd className="text-sm font-medium font-mono text-xs">
                        {systemConfig.embedding_model}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm text-muted-foreground">Cost limit per run</dt>
                      <dd className="text-sm font-medium">
                        ${systemConfig.cost_per_run_limit.toFixed(2)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm text-muted-foreground">Daily cost limit</dt>
                      <dd className="text-sm font-medium">
                        ${systemConfig.cost_daily_limit.toFixed(2)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm text-muted-foreground">Retention (days)</dt>
                      <dd className="text-sm font-medium">
                        transcripts {systemConfig.retention_days.transcripts}, reports{" "}
                        {systemConfig.retention_days.reports}, audit logs{" "}
                        {systemConfig.retention_days.audit_logs}
                      </dd>
                    </div>
                  </dl>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="features">
            <div className="flex items-center justify-between">
              <Card>
                <CardHeader>
                  <CardTitle>Feature Flags</CardTitle>
                  <CardDescription>Toggle features without deploying</CardDescription>
                </CardHeader>
                <CardContent>
                  {featureFlags.length === 0 ? (
                    <div className="text-center py-8">
                      <p className="text-muted-foreground">No feature flags configured</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {featureFlags.map((flag) => (
                        <div key={flag.id} className="flex items-center justify-between p-4 border rounded-lg">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <p className="font-medium">{flag.name}</p>
                              {flag.enabled && <Badge variant="default">Enabled</Badge>}
                              {!flag.enabled && <Badge variant="secondary">Disabled</Badge>}
                            </div>
                            {flag.description && <p className="text-sm text-muted-foreground">{flag.description}</p>}
                            <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
                              <span>Rollout: {flag.rollout_percentage}%</span>
                              <span>Target Roles: {flag.target_roles?.length > 0 ? flag.target_roles.join(", ") : "All"}</span>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Switch
                              checked={flag.enabled}
                              onCheckedChange={(checked) => {
                                // The previous implementation called
                                // setEditingFlag(...) and handleUpdateFlag()
                                // in the same tick, so the update read the
                                // previous state from the closure and the
                                // toggle was a no-op.
                                void handleUpdateFlag({ ...flag, enabled: checked });
                              }}
                            />
                            <Button variant="ghost" size="icon" onClick={() => setEditingFlag(flag)}>
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" onClick={() => void handleDeleteFlag(flag.id)}>
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
              <Dialog open={showCreateFlagDialog} onOpenChange={setShowCreateFlagDialog}>
                <DialogTrigger asChild>
                  <Button><Plus className="mr-2 h-4 w-4" /> New Feature Flag</Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create Feature Flag</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div>
                      <Label htmlFor="flag_name">Name</Label>
                      <Input
                        id="flag_name"
                        value={newFlag.name}
                        onChange={(e) => setNewFlag({...newFlag, name: e.target.value})}
                        placeholder="feature_name"
                      />
                    </div>
                    <div>
                      <Label htmlFor="flag_description">Description</Label>
                      <Textarea
                        id="flag_description"
                        value={newFlag.description}
                        onChange={(e) => setNewFlag({...newFlag, description: e.target.value})}
                        rows={2}
                      />
                    </div>
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <Label htmlFor="flag_rollout">Rollout Percentage</Label>
                        <Input
                          id="flag_rollout"
                          type="number"
                          min={0}
                          max={100}
                          value={newFlag.rollout_percentage}
                          onChange={(e) => setNewFlag({...newFlag, rollout_percentage: parseInt(e.target.value)})}
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <Switch
                          id="flag_enabled"
                          checked={newFlag.enabled}
                          onCheckedChange={(checked) => setNewFlag({...newFlag, enabled: checked})}
                        />
                        <Label htmlFor="flag_enabled">Enabled by Default</Label>
                      </div>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setShowCreateFlagDialog(false)}>Cancel</Button>
                    <Button onClick={handleCreateFlag} disabled={saving || !newFlag.name}>
                      {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : "Create"}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>

              <Dialog
                open={editingFlag !== null}
                onOpenChange={(open) => {
                  if (!open) setEditingFlag(null);
                }}
              >
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Edit Feature Flag</DialogTitle>
                  </DialogHeader>
                  {editingFlag && (
                    <div className="space-y-4 py-4">
                      <div>
                        <Label htmlFor="edit_flag_name">Name</Label>
                        <Input
                          id="edit_flag_name"
                          value={editingFlag.name}
                          onChange={(e) =>
                            setEditingFlag({ ...editingFlag, name: e.target.value })
                          }
                        />
                      </div>
                      <div>
                        <Label htmlFor="edit_flag_description">Description</Label>
                        <Textarea
                          id="edit_flag_description"
                          value={editingFlag.description ?? ""}
                          onChange={(e) =>
                            setEditingFlag({ ...editingFlag, description: e.target.value })
                          }
                          rows={2}
                        />
                      </div>
                      <div className="grid gap-4 md:grid-cols-2">
                        <div>
                          <Label htmlFor="edit_flag_rollout">Rollout Percentage</Label>
                          <Input
                            id="edit_flag_rollout"
                            type="number"
                            min={0}
                            max={100}
                            value={editingFlag.rollout_percentage}
                            onChange={(e) =>
                              setEditingFlag({
                                ...editingFlag,
                                rollout_percentage: parseInt(e.target.value) || 0,
                              })
                            }
                          />
                        </div>
                        <div className="flex items-center gap-2">
                          <Switch
                            id="edit_flag_enabled"
                            checked={editingFlag.enabled}
                            onCheckedChange={(checked) =>
                              setEditingFlag({ ...editingFlag, enabled: checked })
                            }
                          />
                          <Label htmlFor="edit_flag_enabled">Enabled</Label>
                        </div>
                      </div>
                    </div>
                  )}
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setEditingFlag(null)}>
                      Cancel
                    </Button>
                    <Button
                      onClick={() => {
                        if (editingFlag) void handleUpdateFlag(editingFlag);
                      }}
                      disabled={saving}
                    >
                      {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : "Save"}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          </TabsContent>

          <TabsContent value="audit">
            <Card>
              <CardHeader>
                <CardTitle>Audit Logs</CardTitle>
                <CardDescription>System activity and changes</CardDescription>
              </CardHeader>
              <CardContent>
                {auditLogs.length === 0 ? (
                  <div className="text-center py-8">
                    <p className="text-muted-foreground">No audit logs found</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Timestamp</TableHead>
                          <TableHead>User</TableHead>
                          <TableHead>Action</TableHead>
                          <TableHead>Resource</TableHead>
                          <TableHead>IP Address</TableHead>
                          <TableHead>Details</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {auditLogs.map((log) => (
                          <TableRow key={log.id}>
                            <TableCell className="text-sm text-muted-foreground">{formatDate(log.created_at)}</TableCell>
                            <TableCell className="font-mono text-xs">{log.user_id?.slice(0, 8) || "System"}</TableCell>
                            <TableCell><Badge variant="secondary">{log.action}</Badge></TableCell>
                            <TableCell>
                              {log.resource_type && log.resource_id && (
                                <span className="font-mono text-xs">
                                  {log.resource_type}:{log.resource_id.toString().slice(0, 8)}
                                </span>
                              )}
                            </TableCell>
                            <TableCell className="font-mono text-xs">{log.ip_address || "N/A"}</TableCell>
                            <TableCell>
                              <pre className="text-xs font-mono max-w-xs overflow-auto">
                                {JSON.stringify(log.details, null, 2).slice(0, 200)}
                              </pre>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
}