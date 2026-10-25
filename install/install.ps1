<#
.SYNOPSIS
  agent-memory-playbook installer for Windows PowerShell.

.DESCRIPTION
  Installs the full 5-layer memory skill set for every requested tool at once.
  The skills are interdependent - install them as a set, not individually.

  VERIFIED: hermes       -> $env:LOCALAPPDATA\hermes\skills\memory
  VERIFIED: claude-code  -> $HOME\.claude\skills
  VERIFIED: antigravity  -> <workspace>\.agent\skills + <workspace>\AGENTS.md

.PARAMETER Target
  hermes | claude-code | antigravity | all   (default: all)

.PARAMETER Enforce
  Also install the Claude Code memory hooks into this project directory
  (<dir>\.claude\hooks\memory_gate.py + <dir>\.claude\settings.json).

.PARAMETER DryRun
  Print what would happen; touch nothing.
#>
[CmdletBinding()]
param(
    [string[]]$Target = @('all'),
    [string]$Enforce,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$Root      = Split-Path -Parent $PSScriptRoot
$SkillsSrc = Join-Path $Root 'skills'

function Get-HermesHome {
    if ($env:HERMES_HOME) { return $env:HERMES_HOME }
    $dotHermes = Join-Path $HOME '.hermes'
    if (Test-Path $dotHermes) { return $dotHermes }
    return (Join-Path $env:LOCALAPPDATA 'hermes')
}

function Get-SkillsDir([string]$Tool) {
    switch ($Tool) {
        'hermes'      { return (Join-Path (Get-HermesHome) 'skills\memory') }
        'claude-code' { return (Join-Path (Join-Path $HOME '.claude') 'skills') }
        'antigravity' { return (Join-Path $PWD '.agent\skills') }
        default       { throw "unknown target: $Tool" }
    }
}

function Expand-Targets([string[]]$Want) {
    $out = @()
    foreach ($t in $Want) {
        if ($t -eq 'all') { $out += @('hermes', 'claude-code', 'antigravity') }
        elseif ($t -in @('hermes', 'claude-code', 'antigravity')) { $out += $t }
        else { throw "unknown target: $t" }
    }
    return $out
}

function Install-Skills([string]$Tool, [string]$Dest) {
    Write-Host "== $Tool -> $Dest"
    $skillDirs = Get-ChildItem -Path $SkillsSrc -Directory
    if ($DryRun) {
        Write-Host "   (dry-run) would install $($skillDirs.Count) skills (copy)"
        return
    }
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    foreach ($dir in $skillDirs) {
        $target = Join-Path $Dest $dir.Name
        if (Test-Path $target) {
            $stamp  = Get-Date -Format 'yyyyMMddHHmmss'
            $backup = "$target.bak-$stamp"
            Write-Host "   backup: $($dir.Name) -> $(Split-Path -Leaf $backup)"
            Move-Item -Path $target -Destination $backup
        }
        Copy-Item -Path $dir.FullName -Destination $target -Recurse
        Write-Host "   installed $($dir.Name)"
    }
}

function Write-AgentsMd([string]$Workspace) {
    $target = Join-Path $Workspace 'AGENTS.md'
    if ($DryRun) {
        Write-Host "   (dry-run) would write $target"
        return
    }
    $lines = @(
        '# Agent Memory - 5-Layer Playbook',
        '',
        'This workspace has persistent agent memory installed.',
        '',
        'Before any task: query episodic memory, load semantic facts, check for a procedural skill.',
        'After any task: save the outcome, extract new facts, propose a skill after 3 successes.',
        '',
        '## Skills',
        ''
    )
    foreach ($dir in Get-ChildItem -Path $SkillsSrc -Directory) {
        $skillMd = Get-Content (Join-Path $dir.FullName 'SKILL.md') -TotalCount 20
        $desc = ($skillMd | Where-Object { $_ -match '^description:' } | Select-Object -First 1) -replace '^description:\s*', ''
        $lines += "- ``$($dir.Name)`` - $desc"
    }
    $lines += @(
        '',
        '## Savings audit',
        '',
        '```bash',
        'python skills/memory-savings-check/scripts/savings_check.py --memory-dir ./memory --format table',
        '```'
    )
    Set-Content -Path $target -Value $lines -Encoding UTF8
    Write-Host "   wrote $target"
}

$selected = Expand-Targets $Target

Write-Host 'agent-memory-playbook installer'
Write-Host "  source : $SkillsSrc"
Write-Host "  targets: $($selected -join ' ')"
Write-Host ''

foreach ($tool in $selected) {
    Install-Skills $tool (Get-SkillsDir $tool)
    if ($tool -eq 'antigravity') { Write-AgentsMd $PWD }
}

if ($Enforce) {
    Write-Host "== enforcement -> $Enforce"
    $py = Get-Command python, python3 -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $py) { throw '-Enforce needs python on PATH' }
    $gateArgs = @((Join-Path $Root 'enforcement\memory_gate.py'), 'install', '--project', $Enforce)
    if ($DryRun) { $gateArgs += '--dry-run' }
    & $py.Source @gateArgs | ForEach-Object { Write-Host "   $_" }
    if ($LASTEXITCODE -ne 0) { throw "memory_gate install failed ($LASTEXITCODE)" }
}

Write-Host ''
if ($DryRun) { Write-Host 'Dry run complete. Nothing was written.' }
else         { Write-Host 'Done. Restart the target tool so it re-scans its skills directory.' }
