# Script to remove all hardcoded mock data from frontend

Write-Host "Fixing Analytics Page..." -ForegroundColor Yellow
$analyticsContent = Get-Content "frontend/src/app/analytics/page.tsx" -Raw
$analyticsContent = $analyticsContent -replace '(?s)setError\("Failed to load analytics\. Using mock data\."\);.*?}\);', @'
setError("Failed to load analytics. Please check your connection.");
      setAnalytics({
        runs_over_time: [],
        pass_rate_over_time: [],
        regressions_over_time: [],
        cost_over_time: [],
        latency_over_time: [],
        severity_distribution: [],
        category_distribution: [],
        top_failing_tests: [],
      });
'@
Set-Content "frontend/src/app/analytics/page.tsx" $analyticsContent

Write-Host "Fixing Agents Page..." -ForegroundColor Yellow
$agentsContent = Get-Content "frontend/src/app/agents/page.tsx" -Raw
$agentsContent = $agentsContent -replace '(?s)setError\("Failed to load agents\. Using mock data\."\);.*?setAgents\(\[.*?\]\);', 'setError("Failed to load agents. Please check your connection.");      setAgents([]);'
Set-Content "frontend/src/app/agents/page.tsx" $agentsContent

Write-Host "Fixing Suites Page..." -ForegroundColor Yellow
$suitesContent = Get-Content "frontend/src/app/suites/page.tsx" -Raw
$suitesContent = $suitesContent -replace '(?s)setError\("Failed to load suites\. Using mock data\."\);.*?setSuites\(\[.*?\]\);', 'setError("No test suites found. Create your first suite to get started.");      setSuites([]);'
Set-Content "frontend/src/app/suites/page.tsx" $suitesContent

Write-Host "Fixing Redteam Page..." -ForegroundColor Yellow
$redteamContent = Get-Content "frontend/src/app/redteam/page.tsx" -Raw
$redteamContent = $redteamContent -replace '(?s)setError\("Failed to load agents\. Using mock data\."\);.*?setAgents\(\[.*?\]\);', 'setError("No agents available. Configure an agent first.");      setAgents([]);'
Set-Content "frontend/src/app/redteam/page.tsx" $redteamContent

Write-Host "All mock data removed successfully!" -ForegroundColor Green
