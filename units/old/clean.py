from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import NestedCompleter
from src.command_parser import RainbowLexer

from pathlib import Path
import shutil
import sys
import src.file_parser as parser
from src.normalize import normalize
from src.command_parser import command_parser


def help_me(*args):
    return """\nCommand format:
    help or ? - this help;
    parse folder_name - sorts files in the folder;
    good bye or close or exit or . - exit the program"""


def goodbye(*args):
    return 'You have finished working with file_parser'


# Сортуємо лише по типах файлів (True), чи по типах та розширенням (по замовчуванню)
# NOEXT = False


def handle_file(filename: Path, target_folder: Path):
    target_folder.mkdir(exist_ok=True, parents=True)
    filename.replace(target_folder / (normalize(filename.stem) + filename.suffix))


def handle_archive(filename: Path, target_folder: Path):
    # Створюємо теку для архівів
    target_folder.mkdir(exist_ok=True, parents=True)
    # Створюємо теку, куду розпаковуємо архів
    # Беремо суфікс у файлу та прибираємо replace(filename.suffix, '')
    folder_for_file = target_folder / \
                      normalize(filename.name.replace(filename.suffix, ''))
    # Створюємо теку для архіву з іменем файлу

    folder_for_file.mkdir(exist_ok=True, parents=True)
    try:
        shutil.unpack_archive(str(filename.resolve()),
                              str(folder_for_file.resolve()))
    except shutil.ReadError:
        print(f'Обман - це не архів {filename}!')
        folder_for_file.rmdir()
        return None
    filename.unlink()


def handle_folder(folder: Path):
    try:
        folder.rmdir()
    except OSError:
        print(f'Не вдалося видалити теку {folder}')


def main(folder: Path):
    parser.scan(folder)
    for file in parser.IMAGES:
        new_file = folder / 'images' / parser.get_extension(file)
        handle_file(file, new_file)
    for file in parser.AUDIO:
        new_file = folder / 'audio' / parser.get_extension(file)
        handle_file(file, new_file)
    for file in parser.VIDEO:
        new_file = folder / 'video' / parser.get_extension(file)
        handle_file(file, new_file)
    for file in parser.DOCUMENTS:
        new_file = folder / 'documents' / parser.get_extension(file)
        handle_file(file, new_file)
    for file in parser.PROGRAMS:
        new_file = folder / 'programs' / parser.get_extension(file)
        handle_file(file, new_file)

    for file in parser.OTHER:
        if parser.get_extension(file) == normalize(parser.get_extension(file)):
            new_file = folder / 'OTHER' / parser.get_extension(file)
            if not parser.get_extension(file):
                new_file = folder / 'OTHER'
            handle_file(file, new_file)
        else:
            handle_file(file, folder / 'BAD EXTENSIONS')

    for file in parser.ARCHIVES:
        handle_archive(file, folder / 'archives')

    # Виконуємо реверс списку для того, щоб всі теки видалити.
    for folder in parser.FOLDERS[::-1]:
        handle_folder(folder)


# if __name__ == '__main__':

def file_parser(*args):
    if len(args) < 1:
        return 'Please enter a folder name'

    if args[0]:
        folder_for_scan = Path(args[0])
        print(f'\n\033[033mScanning {folder_for_scan}...\033[0m')
        if not folder_for_scan.exists():
            return 'Folder does not exist'
        main(folder_for_scan.resolve())
        return f'Done in folder {folder_for_scan.resolve()}'


# def goodbye(*args):
#     return 'You have finished working with notebook'

COMMANDS_F = {file_parser: ['parse'], help_me: ['?', 'help'], goodbye: ['good bye', 'close', 'exit', '.']}


def start_fp():
    print('\n\033[033mWelcome to file parser!\033[0m')
    print(f"\033[032mType command or '?' for help \033[0m\n")
    while True:
        with open("history.txt", "wb"):
            pass
        user_command = prompt('Enter command >>> ',
                              history=FileHistory('history.txt'),
                              auto_suggest=AutoSuggestFromHistory(),
                              completer=Completer,
                              lexer=RainbowLexer()
                              )
        command, data = command_parser(user_command, COMMANDS_F)
        print(command(*data), '\n')
        if command is goodbye:
            break


Completer = NestedCompleter.from_nested_dict({'help': None, '?': None, 'parse': None, 'good bye': None,
                                              'close': None, 'exit': None, '.': None})
