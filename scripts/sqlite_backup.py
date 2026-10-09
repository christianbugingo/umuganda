#!/usr/bin/env python3
"""Create and restore integrity-checked SQLite backups for this Django project."""

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'umuganda.settings')

import django

django.setup()

from django.conf import settings


def database_path():
    database = settings.DATABASES['default']
    if database['ENGINE'] != 'django.db.backends.sqlite3':
        raise RuntimeError('The configured default database is not SQLite.')
    return Path(database['NAME']).resolve()


def check_integrity(path):
    with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as connection:
        result = connection.execute('PRAGMA integrity_check').fetchone()[0]
    if result != 'ok':
        raise RuntimeError(f'SQLite integrity check failed for {path}: {result}')


def copy_database(source_path, destination_path):
    source_path = Path(source_path)
    destination_path = Path(destination_path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source_path) as source, sqlite3.connect(
        destination_path
    ) as destination:
        source.backup(destination)
    check_integrity(destination_path)


def backup_database(source_path, backup_path):
    backup_path = Path(backup_path)
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f'.{backup_path.name}.',
        suffix='.tmp',
        dir=backup_path.parent,
        delete=False,
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        copy_database(source_path, temporary_path)
        os.replace(temporary_path, backup_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return backup_path


def run_backup(args):
    source = database_path()
    check_integrity(source)
    backup_dir = Path(args.backup_dir or settings.BASE_DIR / 'backups')
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination = Path(args.output) if args.output else (
        backup_dir / f'db-{timestamp}.sqlite3'
    )
    if destination.resolve() == source:
        raise ValueError('The backup path must be different from the database path.')
    backup_database(source, destination)
    print(f'Backup created and verified: {destination.resolve()}')


def run_restore(args):
    source = Path(args.backup).resolve()
    if not source.is_file():
        raise FileNotFoundError(f'Backup file does not exist: {source}')
    check_integrity(source)

    destination = database_path()
    if source == destination:
        raise ValueError('The backup path must be different from the database path.')
    for suffix in ('-wal', '-shm'):
        if Path(f'{destination}{suffix}').exists():
            raise RuntimeError(
                'SQLite sidecar files are present. Stop the web app before restoring.'
            )

    backup_dir = Path(args.backup_dir or settings.BASE_DIR / 'backups')
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    safety_backup = backup_dir / f'pre-restore-{timestamp}.sqlite3'
    if destination.exists():
        try:
            backup_database(destination, safety_backup)
            print(f'Current database saved before restore: {safety_backup.resolve()}')
        except (RuntimeError, sqlite3.Error) as error:
            shutil.copy2(destination, safety_backup)
            print(
                f'Current database could not be integrity-checked ({error}); '
                f'raw copy preserved at {safety_backup.resolve()}',
                file=sys.stderr,
            )

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f'.{destination.name}.',
        suffix='.restore',
        dir=destination.parent,
        delete=False,
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        copy_database(source, temporary_path)
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    print(f'Database restored and verified from: {source}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='action', required=True)

    backup_parser = subparsers.add_parser('backup', help='Create a verified backup')
    backup_parser.add_argument('--backup-dir', help='Backup directory')
    backup_parser.add_argument('--output', help='Explicit backup file path')
    backup_parser.set_defaults(function=run_backup)

    restore_parser = subparsers.add_parser(
        'restore',
        help='Restore a backup (stop the web app first)',
    )
    restore_parser.add_argument('backup', help='SQLite backup file to restore')
    restore_parser.add_argument('--backup-dir', help='Directory for the safety backup')
    restore_parser.set_defaults(function=run_restore)

    args = parser.parse_args()
    try:
        args.function(args)
    except (OSError, RuntimeError, ValueError, sqlite3.Error) as error:
        print(f'Backup operation failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
