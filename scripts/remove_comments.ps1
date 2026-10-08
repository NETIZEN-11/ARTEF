# Script to remove comment lines from all project files

$fileTypes = @('*.py', '*.ts', '*.tsx', '*.js', '*.jsx', '*.sql', '*.yml', '*.yaml', '*.css', '*.html')
$excludeDirs = @('node_modules', '.venv', 'venv', '.git', '.next', 'dist', 'build', '__pycache__', '.ruff_cache', '.pytest_cache', 'coverage')

$files = Get-ChildItem -Path . -Recurse -Include $fileTypes | Where-Object {
    $path = $_.FullName
    $exclude = $false
    foreach ($dir in $excludeDirs) {
        if ($path -match [regex]::Escape($dir)) {
            $exclude = $true
            break
        }
    }
    -not $exclude
}

$count = 0
$totalRemoved = 0

foreach ($file in $files) {
    $count++
    Write-Host "Processing [$count/$($files.Count)]: $($file.Name)" -ForegroundColor Cyan
    
    $content = Get-Content -Path $file.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $content) { continue }
    
    $originalLines = ($content -split "`n").Count
    $newContent = @()
    $lines = $content -split "`n"
    
    $ext = $file.Extension.ToLower()
    
    foreach ($line in $lines) {
        $trimmed = $line.TrimStart()
        
        # Skip empty lines that are just whitespace
        if ($trimmed -eq '') {
            $newContent += $line
            continue
        }
        
        $shouldKeep = $true
        
        # Python comments
        if ($ext -eq '.py') {
            # Keep shebang lines
            if ($trimmed -match '^#!/') {
                $newContent += $line
                continue
            }
            # Skip docstring start/end (but keep them as they're documentation)
            if ($trimmed -match '^("""|' + "'''" + ')') {
                $newContent += $line
                continue
            }
            # Remove lines starting with #
            if ($trimmed -match '^#') {
                $shouldKeep = $false
            }
        }
        
        # JavaScript/TypeScript comments
        if ($ext -in @('.js', '.jsx', '.ts', '.tsx')) {
            # Remove lines starting with //
            if ($trimmed -match '^//') {
                $shouldKeep = $false
            }
            # Remove lines that are just /* */ or /** */ comments on single line
            if ($trimmed -match '^\s*/\*.*\*/\s*$') {
                $shouldKeep = $false
            }
        }
        
        # SQL comments
        if ($ext -eq '.sql') {
            if ($trimmed -match '^--') {
                $shouldKeep = $false
            }
        }
        
        # YAML comments
        if ($ext -in @('.yml', '.yaml')) {
            if ($trimmed -match '^#') {
                $shouldKeep = $false
            }
        }
        
        # CSS comments
        if ($ext -eq '.css') {
            if ($trimmed -match '^\s*/\*.*\*/\s*$') {
                $shouldKeep = $false
            }
        }
        
        # HTML comments
        if ($ext -eq '.html') {
            if ($trimmed -match '^\s*<!--.*-->\s*$') {
                $shouldKeep = $false
            }
        }
        
        if ($shouldKeep) {
            $newContent += $line
        } else {
            $totalRemoved++
        }
    }
    
    $newContentStr = $newContent -join "`n"
    
    # Only write if content changed
    if ($newContentStr -ne $content) {
        Set-Content -Path $file.FullName -Value $newContentStr -NoNewline -Encoding UTF8
        $newLines = ($newContentStr -split "`n").Count
        Write-Host "  Removed $($originalLines - $newLines) lines" -ForegroundColor Green
    }
}

Write-Host "`nDone! Processed $count files, removed $totalRemoved comment lines total." -ForegroundColor Green
