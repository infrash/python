#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moduł interfejsu wiersza poleceń (CLI) dla narzędzia infrash.
Implementuje wszystkie polecenia dostępne z poziomu konsoli.
"""

import os
import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from infrash import __version__
from infrash.core.runner import Runner
from infrash.core.diagnostics import Diagnostics
from infrash.core.repair import Repair
from infrash.repo.git import GitRepo
from infrash.system.os_detect import detect_os
from infrash.system.dependency import check_dependencies, install_dependencies
from infrash.system.dependency_resolver import DependencyResolver
from infrash.utils.logger import setup_logger, get_logger

# Inicjalizacja loggera
setup_logger()
logger = get_logger(__name__)

# Inicjalizacja konsoli rich
console = Console()

# Grupa poleceń CLI
@click.group(help="Infrash - Inteligentny runner do rozwiązywania problemów infrastrukturalnych.")
@click.version_option(__version__, prog_name="infrash")
@click.option("--verbose", "-v", is_flag=True, help="Włącza szczegółowe logowanie.")
@click.option("--quiet", "-q", is_flag=True, help="Wyłącza wszystkie komunikaty (z wyjątkiem błędów).")
@click.option("--config", "-c", type=click.Path(exists=True), help="Ścieżka do pliku konfiguracyjnego.")
@click.pass_context
def cli(ctx, verbose, quiet, config):
    """Grupa główna poleceń CLI infrash."""
    # Konfiguracja kontekstu
    ctx.ensure_object(dict)
    ctx.obj["VERBOSE"] = verbose
    ctx.obj["QUIET"] = quiet
    ctx.obj["CONFIG"] = config

    # Wykrywanie systemu operacyjnego
    ctx.obj["OS_INFO"] = detect_os()

    if verbose and not quiet:
        console.print(f"[bold blue]Infrash[/bold blue] wersja {__version__}")
        console.print(f"Wykryto system: [green]{ctx.obj['OS_INFO']['name']} {ctx.obj['OS_INFO']['version']}[/green]")


# Polecenie inicjalizacji
@cli.command("init", help="Inicjalizuje nowy projekt infrash.")
@click.option("--path", "-p", type=click.Path(), default=".", help="Ścieżka do katalogu projektu.")
@click.option("--template", "-t", type=str, default="default", help="Szablon projektu do użycia.")
@click.pass_context
def init_command(ctx, path, template):
    """Inicjalizuje nowy projekt infrash."""
    try:
        from infrash.core.runner import init_project
        result = init_project(path, template=template)
        if result:
            console.print("[bold green]Projekt został pomyślnie zainicjalizowany![/bold green]")
        else:
            console.print("[bold red]Nie udało się zainicjalizować projektu.[/bold red]")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Błąd podczas inicjalizacji projektu: {str(e)}")
        console.print(f"[bold red]Błąd:[/bold red] {str(e)}")
        sys.exit(1)


# Grupa poleceń dla zarządzania repozytoriami
@cli.group("repo", help="Zarządzanie repozytoriami.")
@click.pass_context
def repo_group(ctx):
    """Grupa poleceń do zarządzania repozytoriami git."""
    pass


@repo_group.command("clone", help="Klonuje repozytorium.")
@click.argument("url", type=str)
@click.option("--path", "-p", type=click.Path(), default=".", help="Ścieżka docelowa.")
@click.option("--branch", "-b", type=str, default=None, help="Gałąź do sklonowania.")
@click.pass_context
def repo_clone(ctx, url, path, branch):
    """Klonuje repozytorium git."""
    try:
        git_repo = GitRepo()
        result = git_repo.clone(url, path, branch=branch)
        if result:
            console.print(f"[bold green]Pomyślnie sklonowano repozytorium:[/bold green] {url}")
        else:
            console.print(f"[bold red]Nie udało się sklonować repozytorium:[/bold red] {url}")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Błąd podczas klonowania repozytorium: {str(e)}")
        console.print(f"[bold red]Błąd:[/bold red] {str(e)}")
        sys.exit(1)


@repo_group.command("update", help="Aktualizuje repozytorium.")
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Ścieżka do repozytorium.")
@click.option("--branch", "-b", type=str, default=None, help="Gałąź do zaktualizowania.")
@click.pass_context
def repo_update(ctx, path, branch):
    """Aktualizuje repozytorium git."""
    try:
        git_repo = GitRepo()
        result = git_repo.update(path, branch=branch)
        if result:
            console.print(f"[bold green]Pomyślnie zaktualizowano repozytorium w:[/bold green] {path}")
        else:
            console.print(f"[bold red]Nie udało się zaktualizować repozytorium w:[/bold red] {path}")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Błąd podczas aktualizacji repozytorium: {str(e)}")
        console.print(f"[bold red]Błąd:[/bold red] {str(e)}")
        sys.exit(1)


# Grupa poleceń dla zarządzania zależnościami
@cli.group(name="deps", help="Zarządzanie zależnościami projektu.")
@click.pass_context
def deps_group(ctx):
    """Grupa poleceń do zarządzania zależnościami projektu."""
    pass


@deps_group.command(name="check", help="Sprawdza zależności projektu.")
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Ścieżka do projektu.")
@click.pass_context
def deps_check(ctx, path):
    """Sprawdza zależności projektu."""
    if not ctx.obj["QUIET"]:
        console.print(Panel("[bold blue]Sprawdzanie zależności projektu[/bold blue]"))
    
    try:
        # Sprawdź zależności
        missing_deps = check_dependencies(path)
        
        if missing_deps:
            console.print("[yellow]Brakujące zależności:[/yellow]")
            for dep in missing_deps:
                console.print(f"  - {dep}")
            
            console.print("\nMożesz zainstalować brakujące zależności za pomocą polecenia:")
            console.print("[bold]infrash deps install[/bold]")
        else:
            console.print("[green]Wszystkie zależności są zainstalowane.[/green]")
    
    except Exception as e:
        logger.error(f"Błąd podczas sprawdzania zależności: {str(e)}")
        console.print(f"[bold red]Błąd:[/bold red] {str(e)}")
        sys.exit(1)


@deps_group.command(name="install", help="Instaluje zależności projektu.")
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Ścieżka do projektu.")
@click.option("--force", "-f", is_flag=True, help="Wymusza reinstalację zależności.")
@click.option("--resolve", "-r", is_flag=True, help="Automatycznie rozwiązuje konflikty wersji.")
@click.pass_context
def deps_install(ctx, path, force, resolve):
    """Instaluje zależności projektu."""
    if not ctx.obj["QUIET"]:
        console.print(Panel("[bold blue]Instalacja zależności projektu[/bold blue]"))
    
    try:
        if resolve:
            # Użyj zaawansowanego resolvera zależności
            resolver = DependencyResolver()
            
            # Znajdź plik requirements.txt
            requirements_path = os.path.join(path, "requirements.txt")
            if not os.path.exists(requirements_path):
                # Szukaj pliku requirements.txt w katalogu
                for root, dirs, files in os.walk(path):
                    if "requirements.txt" in files:
                        requirements_path = os.path.join(root, "requirements.txt")
                        break
            
            if not os.path.exists(requirements_path):
                console.print("[bold red]Błąd:[/bold red] Nie znaleziono pliku requirements.txt")
                sys.exit(1)
            
            console.print(f"Znaleziono plik requirements.txt: {requirements_path}")
            
            # Aktualizuj pip
            console.print("Aktualizacja pip...")
            resolver.update_pip()
            
            # Przetwórz plik requirements.txt
            console.print("Przetwarzanie pliku requirements.txt...")
            success, processed_path = resolver.process_requirements_file(requirements_path)
            
            if not success:
                console.print("[bold red]Błąd:[/bold red] Nie udało się przetworzyć pliku requirements.txt")
                sys.exit(1)
            
            # Instaluj zależności
            console.print("Instalacja zależności...")
            success = resolver.install_requirements_with_retry(processed_path, max_retries=3)
            
            if success:
                console.print("[green]Zależności zostały zainstalowane pomyślnie.[/green]")
            else:
                console.print("[bold red]Błąd:[/bold red] Nie udało się zainstalować wszystkich zależności.")
                sys.exit(1)
        else:
            # Użyj standardowej instalacji zależności
            success = install_dependencies(path, force=force)
            
            if success:
                console.print("[green]Zależności zostały zainstalowane pomyślnie.[/green]")
            else:
                console.print("[bold red]Błąd:[/bold red] Nie udało się zainstalować zależności.")
                sys.exit(1)
    
    except Exception as e:
        logger.error(f"Błąd podczas instalacji zależności: {str(e)}")
        console.print(f"[bold red]Błąd:[/bold red] {str(e)}")
        sys.exit(1)


@deps_group.command(name="resolve", help="Rozwiązuje konflikty wersji zależności.")
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Ścieżka do pliku requirements.txt.")
@click.option("--output", "-o", type=click.Path(), help="Ścieżka do pliku wyjściowego.")
@click.pass_context
def deps_resolve(ctx, path, output):
    """Rozwiązuje konflikty wersji zależności."""
    if not ctx.obj["QUIET"]:
        console.print(Panel("[bold blue]Rozwiązywanie konfliktów wersji zależności[/bold blue]"))
    
    try:
        # Sprawdź, czy podana ścieżka to plik
        if os.path.isdir(path):
            # Szukaj pliku requirements.txt w katalogu
            requirements_path = os.path.join(path, "requirements.txt")
            if not os.path.exists(requirements_path):
                # Szukaj pliku requirements.txt w projekcie
                for root, dirs, files in os.walk(path):
                    if "requirements.txt" in files:
                        requirements_path = os.path.join(root, "requirements.txt")
                        break
        else:
            requirements_path = path
        
        if not os.path.exists(requirements_path):
            console.print("[bold red]Błąd:[/bold red] Nie znaleziono pliku requirements.txt")
            sys.exit(1)
        
        console.print(f"Przetwarzanie pliku: {requirements_path}")
        
        # Inicjalizuj resolver zależności
        resolver = DependencyResolver()
        
        # Przetwórz plik requirements.txt
        success, processed_path = resolver.process_requirements_file(requirements_path, output)
        
        if success:
            console.print(f"[green]Plik został przetworzony pomyślnie: {processed_path}[/green]")
            
            # Wyświetl zmiany
            with open(requirements_path, "r") as f_orig:
                orig_content = f_orig.readlines()
            
            with open(processed_path, "r") as f_proc:
                proc_content = f_proc.readlines()
            
            if orig_content != proc_content:
                console.print("\n[yellow]Wprowadzone zmiany:[/yellow]")
                
                table = Table(show_header=True)
                table.add_column("Oryginalna wersja", style="cyan")
                table.add_column("Nowa wersja", style="green")
                
                for orig_line, proc_line in zip(orig_content, proc_content):
                    orig_line = orig_line.strip()
                    proc_line = proc_line.strip()
                    
                    if orig_line != proc_line and not orig_line.startswith("#") and not proc_line.startswith("#"):
                        table.add_row(orig_line, proc_line)
                
                console.print(table)
            else:
                console.print("[green]Nie wykryto konfliktów wersji.[/green]")
        else:
            console.print("[bold red]Błąd:[/bold red] Nie udało się przetworzyć pliku requirements.txt")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Błąd podczas rozwiązywania konfliktów wersji: {str(e)}")
        console.print(f"[bold red]Błąd:[/bold red] {str(e)}")
        sys.exit(1)


# Polecenie instalacji
@cli.command("install", help="Instaluje zależności projektu.")
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Ścieżka do projektu.")
@click.option("--force", "-f", is_flag=True, help="Wymusza reinstalację istniejących zależności.")
@click.pass_context
def install_command(ctx, path, force):
    """Instaluje zależności projektu."""
    try:
        from infrash.core.installer import Installer
        installer = Installer()
        result = installer.install_dependencies(path, force=force)

        if result:
            console.print("[bold green]Pomyślnie zainstalowano zależności![/bold green]")
        else:
            console.print("[bold yellow]Nie wszystkie zależności zostały zainstalowane.[/bold yellow]")
            if not ctx.obj["QUIET"]:
                console.print("Uruchom 'infrash diagnose' aby zdiagnozować problemy.")
    except Exception as e:
        logger.error(f"Błąd podczas instalacji zależności: {str(e)}")
        console.print(f"[bold red]Błąd:[/bold red] {str(e)}")
        sys.exit(1)


# Polecenie uruchamiania
@cli.command("start", help="Uruchamia aplikację.")
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Ścieżka do projektu.")
@click.option("--env", "-e", type=str, default="development", help="Środowisko uruchomieniowe.")
@click.option("--diagnostic-level", "-d", type=click.Choice(['none', 'basic', 'full']),
              default="basic", help="Poziom diagnostyki.")
@click.pass_context
def start_command(ctx, path, env, diagnostic_level):
    """Uruchamia aplikację."""
    try:
        runner = Runner()
        result = runner.start(path, env=env, diagnostic_level=diagnostic_level)

        if result:
            console.print("[bold green]Aplikacja została uruchomiona pomyślnie![/bold green]")
        else:
            console.print("[bold red]Nie udało się uruchomić aplikacji.[/bold red]")
            if not ctx.obj["QUIET"]:
                console.print("Uruchom 'infrash diagnose' aby zdiagnozować problemy.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania aplikacji: {str(e)}")
        console.print(f"[bold red]Błąd:[/bold red] {str(e)}")
        sys.exit(1)


# Polecenie zatrzymania
@cli.command("stop", help="Zatrzymuje uruchomioną aplikację.")
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Ścieżka do projektu.")
@click.option("--force", "-f", is_flag=True, help="Wymusza zatrzymanie w przypadku problemów.")
@click.pass_context
def stop_command(ctx, path, force):
    """Zatrzymuje uruchomioną aplikację."""
    try:
        runner = Runner()
        result = runner.stop(path, force=force)

        if result:
            console.print("[bold green]Aplikacja została zatrzymana pomyślnie![/bold green]")
        else:
            console.print("[bold red]Nie udało się zatrzymać aplikacji.[/bold red]")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Błąd podczas zatrzymywania aplikacji: {str(e)}")
        console.print(f"[bold red]Błąd:[/bold red] {str(e)}")
        sys.exit(1)


# Polecenie restartu
@cli.command("restart", help="Restartuje aplikację.")
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Ścieżka do projektu.")
@click.option("--env", "-e", type=str, default=None, help="Środowisko uruchomieniowe.")
@click.option("--force", "-f", is_flag=True, help="Wymusza restart w przypadku problemów.")
@click.pass_context
def restart_command(ctx, path, env, force):
    """Restartuje aplikację."""
    try:
        runner = Runner()
        result = runner.restart(path, env=env, force=force)

        if result:
            console.print("[bold green]Aplikacja została zrestartowana pomyślnie![/bold green]")
        else:
            console.print("[bold red]Nie udało się zrestartować aplikacji.[/bold red]")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Błąd podczas restartowania aplikacji: {str(e)}")
        console.print(f"[bold red]Błąd:[/bold red] {str(e)}")
        sys.exit(1)


# Polecenie statusu
@cli.command("status", help="Wyświetla status aplikacji.")
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Ścieżka do projektu.")
@click.option("--detailed", "-d", is_flag=True, help="Pokazuje szczegółowe informacje.")
@click.pass_context
def status_command(ctx, path, detailed):
    """Wyświetla status aplikacji."""
    try:
        runner = Runner()
        status = runner.status(path, detailed=detailed)

        # Tworzenie tabeli statusu
        table = Table(title="Status Aplikacji")
        table.add_column("Komponent", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Szczegóły", style="yellow")

        for component, info in status.items():
            component_status = info.get("status", "nieznany")
            details = info.get("details", "")

            status_style = "green" if component_status == "running" else "red"
            table.add_row(component, f"[{status_style}]{component_status}[/{status_style}]", details)

        console.print(table)

    except Exception as e:
        logger.error(f"Błąd podczas sprawdzania statusu: {str(e)}")
        console.print(f"[bold red]Błąd:[/bold red] {str(e)}")
        sys.exit(1)


# Polecenie diagnostyki
@cli.command("diagnose", help="Diagnozuje problemy w projekcie.")
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Ścieżka do projektu.")
@click.option("--auto-fix", "-f", is_flag=True, help="Automatycznie naprawia znalezione problemy.")
@click.option("--level", "-l", type=click.Choice(['basic', 'advanced', 'full']),
              default="basic", help="Poziom diagnostyki.")
@click.pass_context
def diagnose_command(ctx, path, auto_fix, level):
    """Diagnozuje problemy w projekcie."""
    try:
        diagnostics = Diagnostics()
        issues = diagnostics.run(path, level=level)

        if not issues:
            console.print("[bold green]Nie znaleziono żadnych problemów![/bold green]")
            return

        # Wyświetlanie znalezionych problemów
        console.print(f"[bold yellow]Znaleziono {len(issues)} potencjalnych problemów:[/bold yellow]")

        for i, issue in enumerate(issues, 1):
            panel = Panel(
                f"[bold]{issue.get('title', 'Problem')}\n\n[/bold]"
                f"{issue.get('description', 'Brak opisu')}\n\n"
                f"[dim]Możliwe rozwiązanie: {issue.get('solution', 'Brak sugestii')}[/dim]",
                title=f"Problem #{i}",
                border_style="yellow"
            )
            console.print(panel)

        # Automatyczna naprawa, jeśli wybrano
        if auto_fix and issues:
            console.print("[bold]Rozpoczynam automatyczną naprawę problemów...[/bold]")
            repair_tool = Repair()
            fixed = 0

            for issue in issues:
                if repair_tool.fix(issue):
                    fixed += 1
                    console.print(f"[green]✓ Naprawiono: {issue.get('title', 'Problem')}[/green]")
                else:
                    console.print(f"[red]✗ Nie udało się naprawić: {issue.get('title', 'Problem')}[/red]")

            console.print(f"[bold]Naprawiono {fixed} z {len(issues)} problemów.[/bold]")

            # Sprawdzenie, czy wszystkie problemy zostały rozwiązane
            if fixed == len(issues):
                console.print("[bold green]Wszystkie problemy zostały naprawione![/bold green]")
            else:
                console.print("[bold yellow]Niektóre problemy wymagają ręcznej interwencji.[/bold yellow]")
                if not ctx.obj["QUIET"]:
                    console.print("Użyj 'infrash repair --issue=ID' aby naprawić konkretny problem ręcznie.")
    except Exception as e:
        logger.error(f"Błąd podczas diagnostyki: {str(e)}")
        console.print(f"[bold red]Błąd:[/bold red] {str(e)}")
        sys.exit(1)


# Polecenie naprawy
@cli.command("repair", help="Naprawia konkretny problem.")
@click.option("--issue", "-i", type=str, help="ID problemu do naprawy.")
@click.option("--all", "-a", is_flag=True, help="Naprawia wszystkie znalezione problemy.")
@click.option("--path", "-p", type=click.Path(exists=True), default=".", help="Ścieżka do projektu.")
@click.pass_context
def repair_command(ctx, issue, all, path):
    """Naprawia problemy w projekcie."""
    try:
        # Najpierw diagnozujemy, aby znaleźć problemy
        diagnostics = Diagnostics()
        issues = diagnostics.run(path, level="basic")

        if not issues:
            console.print("[bold green]Nie znaleziono żadnych problemów do naprawy![/bold green]")
            return

        repair_tool = Repair()
        fixed = 0

        if all:
            # Naprawiamy wszystkie problemy
            console.print("[bold]Rozpoczynam naprawę wszystkich problemów...[/bold]")
            for issue_item in issues:
                if repair_tool.fix(issue_item):
                    fixed += 1
                    console.print(f"[green]✓ Naprawiono: {issue_item.get('title', 'Problem')}[/green]")
                else:
                    console.print(f"[red]✗ Nie udało się naprawić: {issue_item.get('title', 'Problem')}[/red]")

        elif issue:
            # Naprawiamy konkretny problem
            issue_found = False
            for issue_item in issues:
                if issue_item.get("id") == issue:
                    issue_found = True
                    console.print(f"[bold]Próba naprawy problemu: {issue_item.get('title', 'Problem')}[/bold]")
                    if repair_tool.fix(issue_item):
                        fixed += 1
                        console.print(f"[green]✓ Problem został naprawiony pomyślnie![/green]")
                    else:
                        console.print(f"[red]✗ Nie udało się naprawić problemu.[/red]")
                    break

            if not issue_found:
                console.print(f"[bold red]Nie znaleziono problemu o ID: {issue}[/bold red]")
                return

        else:
            # Wyświetlamy listę problemów, jeśli nie podano konkretnego ID ani flagi --all
            console.print("[bold yellow]Znalezione problemy:[/bold yellow]")
            table = Table()
            table.add_column("ID", style="cyan")
            table.add_column("Problem", style="yellow")
            table.add_column("Sugerowane rozwiązanie", style="green")

            for issue_item in issues:
                table.add_row(
                    issue_item.get("id", "???"),
                    issue_item.get("title", "Nieznany problem"),
                    issue_item.get("solution", "Brak sugestii")
                )

            console.print(table)
            console.print("Użyj 'infrash repair --issue=ID' aby naprawić konkretny problem.")
            console.print("Użyj 'infrash repair --all' aby naprawić wszystkie problemy jednocześnie.")
            return

        # Podsumowanie
        if fixed > 0:
            console.print(f"[bold green]Naprawiono {fixed} {'problem' if fixed == 1 else 'problemy/problemów'}.[/bold green]")
        else:
            console.print("[bold red]Nie naprawiono żadnych problemów.[/bold red]")

    except Exception as e:
        logger.error(f"Błąd podczas naprawy: {str(e)}")
        console.print(f"[bold red]Błąd:[/bold red] {str(e)}")
        sys.exit(1)


# Grupa poleceń dla zarządzania rozwiązaniami
@cli.group("solutions", help="Zarządzanie bazą danych rozwiązań.")
@click.pass_context
def solutions_group(ctx):
    """Grupa poleceń do zarządzania bazą danych rozwiązań."""
    pass


@solutions_group.command("update", help="Aktualizuje bazę danych rozwiązań.")
@click.option("--force", "-f", is_flag=True, help="Wymusza pełną aktualizację.")
@click.pass_context
def solutions_update(ctx, force):
    """Aktualizuje bazę danych rozwiązań."""
    try:
        from infrash.utils.database import SolutionsDB
        db = SolutionsDB()
        result = db.update(force=force)

        if result:
            console.print("[bold green]Baza danych rozwiązań została zaktualizowana![/bold green]")
        else:
            console.print("[bold red]Nie udało się zaktualizować bazy danych rozwiązań.[/bold red]")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Błąd podczas aktualizacji bazy danych: {str(e)}")
        console.print(f"[bold red]Błąd:[/bold red] {str(e)}")
        sys.exit(1)


@solutions_group.command("list", help="Wyświetla dostępne rozwiązania.")
@click.option("--filter", "-f", type=str, help="Filtruje rozwiązania po słowie kluczowym.")
@click.option("--os", type=str, help="Filtruje rozwiązania po systemie operacyjnym.")
@click.pass_context
def solutions_list(ctx, filter, os):
    """Wyświetla dostępne rozwiązania w bazie danych."""
    try:
        from infrash.utils.database import SolutionsDB
        db = SolutionsDB()
        solutions = db.list(filter=filter, os=os)

        if not solutions:
            console.print("[yellow]Nie znaleziono rozwiązań spełniających kryteria.[/yellow]")
            return

        table = Table(title="Dostępne Rozwiązania")
        table.add_column("ID", style="cyan")
        table.add_column("Problem", style="yellow")
        table.add_column("System", style="green")
        table.add_column("Kategoria", style="blue")

        for solution in solutions:
            table.add_row(
                solution.get("id", "???"),
                solution.get("title", "Nieznane rozwiązanie"),
                solution.get("os", "Wszystkie"),
                solution.get("category", "Ogólne")
            )

        console.print(table)

    except Exception as e:
        logger.error(f"Błąd podczas listowania rozwiązań: {str(e)}")
        console.print(f"[bold red]Błąd:[/bold red] {str(e)}")
        sys.exit(1)


# Grupa poleceń dla zdalnych operacji
@cli.group("remote", help="Zarządzanie zdalnymi wdrożeniami i operacjami.")
@click.pass_context
def remote_group(ctx):
    """Grupa poleceń do zarządzania zdalnymi wdrożeniami i operacjami."""
    pass


@remote_group.command("deploy", help="Wdraża projekt na zdalnym hoście.")
@click.option("--host", required=True, help="Adres IP lub nazwa hosta.")
@click.option("--user", required=True, help="Nazwa użytkownika SSH.")
@click.option("--password", help="Hasło SSH (opcjonalne jeśli używasz klucza).")
@click.option("--key", help="Ścieżka do pliku klucza prywatnego SSH.")
@click.option("--port", type=int, default=22, help="Port SSH (domyślnie: 22).")
@click.option("--repo", required=True, help="URL repozytorium Git do wdrożenia.")
@click.option("--branch", "-b", help="Gałąź do sklonowania (opcjonalne).")
@click.option("--no-deps", is_flag=True, help="Nie instaluj zależności systemowych.")
@click.option("--resolve-deps", "-r", is_flag=True, help="Automatycznie rozwiązuj konflikty wersji zależności.")
@click.option("--retry", type=int, default=3, help="Liczba prób ponownego połączenia w przypadku błędu.")
@click.pass_context
def remote_deploy(ctx, host, user, password, key, port, repo, branch, no_deps, resolve_deps, retry):
    """Wdraża projekt na zdalnym hoście."""
    try:
        from infrash.remote.remote_manager import RemoteManager
        
        if not ctx.obj["QUIET"]:
            console.print(Panel(f"[bold blue]Wdrażanie projektu na hoście {host}[/bold blue]"))
            console.print(f"Repozytorium: {repo}")
            if branch:
                console.print(f"Gałąź: {branch}")
            console.print(f"Automatyczne rozwiązywanie konfliktów wersji: {'Tak' if resolve_deps else 'Nie'}")
        
        remote_manager = RemoteManager()
        success = remote_manager.deploy(
            hostname=host,
            username=user,
            password=password,
            key_filename=key,
            port=port,
            repo_url=repo,
            branch=branch,
            install_deps=not no_deps,
            resolve_deps=resolve_deps,
            max_retries=retry
        )
        
        if success:
            console.print(f"[bold green]Pomyślnie wdrożono projekt na hoście {host}![/bold green]")
        else:
            console.print(f"[bold red]Nie udało się wdrożyć projektu na hoście {host}.[/bold red]")
            
            # Uruchom diagnostykę w przypadku błędu
            from infrash.core.diagnostics import Diagnostics
            diagnostics = Diagnostics()
            
            # Sprawdź połączenie sieciowe
            network_status = diagnostics.check_network_connectivity(host)
            if not network_status["success"]:
                console.print(f"[yellow]Problem z połączeniem sieciowym:[/yellow] {network_status['message']}")
                console.print(f"[yellow]Sugestia:[/yellow] {network_status['suggestion']}")
            
            # Sprawdź dostępność narzędzi
            tools_status = diagnostics.check_required_tools(["ssh", "git"])
            if not tools_status["success"]:
                console.print(f"[yellow]Brakujące narzędzia:[/yellow] {', '.join(tools_status['missing'])}")
                console.print(f"[yellow]Sugestia:[/yellow] {tools_status['suggestion']}")
            
            # Sugestie naprawy
            console.print("\n[bold yellow]Sugestie rozwiązania problemów:[/bold yellow]")
            console.print("1. Sprawdź połączenie sieciowe z hostem zdalnym.")
            console.print("2. Upewnij się, że podane dane logowania są poprawne.")
            console.print("3. Spróbuj użyć opcji --resolve-deps, aby automatycznie rozwiązywać konflikty wersji.")
            console.print("4. Zwiększ liczbę prób ponownego połączenia za pomocą opcji --retry.")
            
            sys.exit(1)
    except ImportError as e:
        logger.error(f"Brak wymaganych modułów: {str(e)}")
        console.print(f"[bold red]Błąd:[/bold red] Brak wymaganych modułów. Instalowanie...")
        
        # Auto-naprawa - instalacja brakujących zależności
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko", "requests", "packaging"])
            console.print("[green]Zainstalowano brakujące zależności. Spróbuj ponownie uruchomić polecenie.[/green]")
        except Exception as install_error:
            console.print(f"[bold red]Nie udało się zainstalować zależności:[/bold red] {str(install_error)}")
        
        sys.exit(1)
    except Exception as e:
        logger.error(f"Błąd podczas wdrażania: {str(e)}")
        console.print(f"[bold red]Błąd:[/bold red] {str(e)}")
        sys.exit(1)


@remote_group.command("run", help="Uruchamia polecenie na zdalnym hoście.")
@click.option("--host", required=True, help="Adres IP lub nazwa hosta.")
@click.option("--user", required=True, help="Nazwa użytkownika SSH.")
@click.option("--password", help="Hasło SSH (opcjonalne jeśli używasz klucza).")
@click.option("--key", help="Ścieżka do pliku klucza prywatnego SSH.")
@click.option("--port", type=int, default=22, help="Port SSH (domyślnie: 22).")
@click.option("--command", "-c", required=True, help="Polecenie do uruchomienia.")
@click.pass_context
def remote_run(ctx, host, user, password, key, port, command):
    """Uruchamia polecenie na zdalnym hoście."""
    try:
        from infrash.remote.remote_manager import RemoteManager
        
        remote_manager = RemoteManager()
        success, ssh_client = remote_manager.connect(
            hostname=host,
            username=user,
            password=password,
            key_filename=key,
            port=port
        )
        
        if not success or ssh_client is None:
            console.print(f"[bold red]Nie udało się połączyć z hostem {host}.[/bold red]")
            
            # Uruchom diagnostykę w przypadku błędu
            from infrash.core.diagnostics import Diagnostics
            diagnostics = Diagnostics()
            
            # Sprawdź połączenie sieciowe
            network_status = diagnostics.check_network_connectivity(host)
            if not network_status["success"]:
                console.print(f"[yellow]Problem z połączeniem sieciowym:[/yellow] {network_status['message']}")
                console.print(f"[yellow]Sugestia:[/yellow] {network_status['suggestion']}")
            
            sys.exit(1)
        
        success, stdout, stderr = remote_manager.run_command(ssh_client, command)
        
        if success:
            console.print(f"[bold green]Pomyślnie wykonano polecenie na hoście {host}![/bold green]")
            if stdout:
                console.print(Panel(stdout, title="Standardowe wyjście", border_style="green"))
        else:
            console.print(f"[bold red]Nie udało się wykonać polecenia na hoście {host}.[/bold red]")
            if stderr:
                console.print(Panel(stderr, title="Błędy", border_style="red"))
            sys.exit(1)
            
    except ImportError as e:
        logger.error(f"Brak wymaganych modułów: {str(e)}")
        console.print(f"[bold red]Błąd:[/bold red] Brak wymaganych modułów. Instalowanie...")
        
        # Auto-naprawa - instalacja brakujących zależności
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko"])
            console.print("[green]Zainstalowano brakujące zależności. Spróbuj ponownie uruchomić polecenie.[/green]")
        except Exception as install_error:
            console.print(f"[bold red]Nie udało się zainstalować zależności:[/bold red] {str(install_error)}")
        
        sys.exit(1)
    except Exception as e:
        logger.error(f"Błąd podczas wykonywania polecenia: {str(e)}")
        console.print(f"[bold red]Błąd:[/bold red] {str(e)}")
        sys.exit(1)


# Główna funkcja wejściowa
if __name__ == "__main__":
    cli(obj={})