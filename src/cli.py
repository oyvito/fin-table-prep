"""
CLI for fin-stat-prep.

Kommandolinje-grensesnitt med underkommandoer:
- generate: Generer prep-script fra input/output filer
- validate: Valider en statistikktabell
- codelist: Administrer kodelister
"""

import argparse
import sys
from pathlib import Path


def cmd_generate(args):
    """Generer prep-script."""
    from .core import generate_prep_script
    
    print(f"=== Genererer prep-script for {args.table_code} ===\n")
    
    generate_prep_script(
        input_files=args.input_files,
        output_file=args.output,
        table_code=args.table_code,
        input_sheets=args.input_sheets,
        output_sheet=args.output_sheet
    )


def cmd_validate(args):
    """Valider en statistikktabell."""
    import pandas as pd
    
    # Import validator
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from validate_table import TableValidator
    
    print(f"=== Validerer {args.file} ===\n")
    
    try:
        df = pd.read_excel(args.file, sheet_name=args.sheet or 0)
        
        validator = TableValidator()
        
        # Standardisering
        suggestions = validator.suggest_column_standardization(df)
        if suggestions:
            print("📝 FORSLAG TIL STANDARDISERING:")
            for current, suggested in suggestions.items():
                print(f"  {current} → {suggested}")
            print()
        
        # Datatyper
        type_issues = validator.validate_data_types(df)
        if type_issues:
            print("⚠️  DATATYPE-ADVARSLER:")
            for issue in type_issues:
                print(f"  {issue['column']}: {issue['issue']}")
            print()
        
        # Geografisk koding
        geo_issues = validator.validate_geographic_coding(df)
        if geo_issues:
            print("🗺️  GEOGRAFISK KODING:")
            for issue in geo_issues:
                print(f"  {issue['column']}: {issue['issue']}")
            print()
        
        if not suggestions and not type_issues and not geo_issues:
            print("✅ Ingen problemer funnet!")
        
    except Exception as e:
        print(f"❌ Feil ved validering: {e}")
        sys.exit(1)


def cmd_codelist_list(args):
    """List tilgjengelige kodelister."""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from codelist_manager import CodelistManager
    
    manager = CodelistManager()
    
    print("=== Tilgjengelige kodelister ===\n")
    
    if not manager.codelists:
        print("Ingen kodelister funnet i 'kodelister/' mappen.")
        return
    
    for name, codelist in manager.codelists.items():
        desc = codelist.get('description', 'Ingen beskrivelse')
        num_mappings = len(codelist.get('mappings', {}))
        print(f"📋 {name}")
        print(f"   {desc}")
        print(f"   Antall mappings: {num_mappings}")
        print()


def cmd_codelist_show(args):
    """Vis detaljer for en kodeliste."""
    import json
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from codelist_manager import CodelistManager
    
    manager = CodelistManager()
    
    # Finn kodelisten
    codelist = None
    for name, cl in manager.codelists.items():
        if args.name.lower() in name.lower():
            codelist = cl
            break
    
    if not codelist:
        print(f"❌ Kodeliste '{args.name}' ikke funnet.")
        print("Bruk 'fin-prep codelist list' for å se tilgjengelige kodelister.")
        sys.exit(1)
    
    print(f"=== {codelist.get('name', 'Ukjent')} ===\n")
    print(f"Beskrivelse: {codelist.get('description', '-')}")
    print(f"Kilde: {codelist.get('source', '-')}")
    print(f"Sist oppdatert: {codelist.get('last_updated', '-')}")
    print()
    
    if args.verbose:
        print("Mappings:")
        mappings = codelist.get('mappings', {})
        for k, v in list(mappings.items())[:20]:
            print(f"  {k} → {v}")
        if len(mappings) > 20:
            print(f"  ... og {len(mappings) - 20} til")


def create_parser():
    """Opprett argument-parser."""
    parser = argparse.ArgumentParser(
        prog='fin-prep',
        description='fin-stat-prep: Automatisk generering av prep-scripts for statistikktabeller'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Tilgjengelige kommandoer')
    
    # generate kommando
    gen_parser = subparsers.add_parser('generate', help='Generer prep-script')
    gen_parser.add_argument('input_files', nargs='+', help='Input Excel-filer')
    gen_parser.add_argument('--output', '-o', required=True, help='Output Excel-fil (referanse)')
    gen_parser.add_argument('--table-code', '-t', required=True, help='Tabellkode (f.eks. OK-SYS001)')
    gen_parser.add_argument('--input-sheets', nargs='+', help='Sheet-navn for input-filer')
    gen_parser.add_argument('--output-sheet', help='Sheet-navn for output-fil')
    
    # validate kommando
    val_parser = subparsers.add_parser('validate', help='Valider en statistikktabell')
    val_parser.add_argument('file', help='Excel-fil å validere')
    val_parser.add_argument('--sheet', '-s', help='Sheet-navn')
    
    # codelist kommando med under-kommandoer
    cl_parser = subparsers.add_parser('codelist', help='Administrer kodelister')
    cl_subparsers = cl_parser.add_subparsers(dest='codelist_command', help='Kodeliste-kommandoer')
    
    cl_list = cl_subparsers.add_parser('list', help='List tilgjengelige kodelister')
    
    cl_show = cl_subparsers.add_parser('show', help='Vis detaljer for en kodeliste')
    cl_show.add_argument('name', help='Navn på kodelisten')
    cl_show.add_argument('--verbose', '-v', action='store_true', help='Vis mappings')
    
    return parser


def main():
    """Hovedfunksjon for CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command == 'generate':
        cmd_generate(args)
    elif args.command == 'validate':
        cmd_validate(args)
    elif args.command == 'codelist':
        if args.codelist_command == 'list':
            cmd_codelist_list(args)
        elif args.codelist_command == 'show':
            cmd_codelist_show(args)
        else:
            parser.parse_args(['codelist', '--help'])
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
