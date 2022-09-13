"""Модуль для роботи з нотатками"""
import datetime
import re

from prompt_toolkit import prompt
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.history import FileHistory

from units.command_parser import RainbowLexer
from units.paginator import Paginator, hyphenation_string

from src.db import session
from src.models import Note, Tag
from sqlalchemy.exc import NoResultFound
from sqlalchemy import and_, not_


class DateIsNotValid(Exception):
    """You cannot add an invalid date"""


class InputError:
    """Клас для виклику помилки при введенні невірного даних"""

    def __init__(self, func) -> None:
        self.func = func

    def __call__(self, *args):
        try:
            return self.func(*args)
        except KeyError:
            return 'Error! Note not found!'
        except ValueError:
            return 'Error! Incorrect argument!'
        except DateIsNotValid:
            return 'Error! Date is not valid'
        except IndexError:
            return 'Error! Incorrect argument!'
        except NoResultFound:
            return 'Error! Note not found'


def view_note(note):
    id_ = note.id
    text_ = note.text
    date_ = datetime.date.strftime(note.execution_date, '%d %b %Y') if note.execution_date else '     -    '
    tags_db = session.query(Tag).filter(Tag.note_id == id_).order_by(Tag.tag).all()
    tags = [tag.tag for tag in tags_db]
    return f"\033[34mID:\033[0m {id_:^10} {' ' * 47} \033[34mDate:\033[0m {date_}\n" \
           f"\033[34mTags:\033[0m {', '.join(tags)}\n" \
           f"{hyphenation_string(text_)}"


@InputError
def add_note(*args):
    """Додає нотатку"""
    note_text = ' '.join(args)
    note = Note(text=note_text)
    session.add(note)
    session.commit()
    return f'Note ID:{note.id} added'


@InputError
def change_note(*args):
    id_note, new_text = int(args[0]), ' '.join(args[1:])
    note = session.query(Note).filter(Note.id == id_note).one()
    note.text = new_text
    session.commit()
    return f'Note ID:{id_note} changed'


@InputError
def del_note(*args):
    id_note = int(args[0])
    session.query(Note).filter(Note.id == id_note).one()  # перевірка на існування
    yes_no = input(f'Are you sure you want to delete the note ID:{id_note}? (Y/n) ')
    if yes_no == 'Y':
        session.query(Note).filter(Note.id == id_note).delete()
        session.commit()
        return f'Note ID:{id_note} deleted'
    else:
        return 'Note not deleted'


@InputError
def add_date(*args):
    """Додає дату нотатки"""
    id_note, exec_date_str = int(args[0]), args[1]
    note = session.query(Note).filter(Note.id == id_note).one()  # перевірка на існування
    try:
        exec_date = datetime.datetime.strptime(exec_date_str, '%Y-%m-%d').date()
    except ValueError:
        try:
            exec_date = datetime.datetime.strptime(exec_date_str, '%d.%m.%Y').date()
        except ValueError:
            raise DateIsNotValid
    note.execution_date = exec_date
    session.commit()
    return f'Date {exec_date} added to note ID:{id_note}'


@InputError
def add_tag(*args):
    id_note = int(args[0])
    session.query(Note).filter(Note.id == id_note).one()  # перевірка на існування
    note_tags = re.sub(r'[;,.!?]', ' ', ' '.join(args[1:])).title().split()
    note_tags = list(set(note_tags))
    # Визначаємо існуючі теги для нотатки
    all_note_tags = []
    tag_all = session.query(Tag).filter(Tag.note_id == id_note).all()
    for tag in tag_all:
        all_note_tags.append(tag.tag)
    # Додавання тегів, яких ще немає
    result_tag = []
    for tag in note_tags:
        if not tag in all_note_tags:
            new_tag = Tag(note_id=id_note, tag=tag)
            session.add(new_tag)
            session.commit()
            result_tag.append(tag)
    if result_tag:
        return f'Tags {", ".join(sorted(result_tag))} added to note ID:{id_note}'
    else:
        return f'No tags added to note ID:{id_note}'


@InputError
def done_note(*args):
    """Помічає нотатку як виконану"""
    id_note = int(args[0])
    note = session.query(Note).filter(Note.id == id_note).one()  # перевірка на існування
    note.is_done = True
    session.commit()
    return f'Note ID:{id_note} marked as done'


@InputError
def return_note(*args):
    """Помічає нотатку як невиконану"""
    id_note = int(args[0])
    note = session.query(Note).filter(Note.id == id_note).one()  # перевірка на існування
    note.is_done = False
    session.commit()
    return f'Note ID:{id_note} marked as not done'


def show_all(*args):
    """Повертає всі нотатки"""
    notes = session.query(Note).filter(not_(Note.is_done)).order_by(Note.id).all()
    result = 'List of all notes:\n'
    print_list = Paginator(notes).get_view(func=view_note)
    for item in print_list:
        if item is None:
            return 'No notes found'
        else:
            result += f'{item}'
    return result


def show_archiv(*args):
    """Повертає нотатки з архіву"""
    notes = session.query(Note).filter(Note.is_done).order_by(Note.id).all()
    result = 'List of all archived notes:\n'
    print_list = Paginator(notes).get_view(func=view_note)
    for item in print_list:
        if item is None:
            return 'No notes found'
        else:
            result += f'{item}'
    return result


def find_note(*args):
    """Повертає нотатки за входженням в текст"""
    subtext = args[0]
    notes = session.query(Note).filter(and_(not_(Note.is_done), Note.text.ilike(f'%{subtext}%'))).order_by(Note.id).all()
    result = f'List of notes with text "{subtext}":\n'
    print_list = Paginator(notes).get_view(func=view_note)
    for item in print_list:
        if item is None:
            return 'No notes found'
        else:
            result += f'{item}'
    return result


@InputError
def show_date(*args):
    """Повертає нотатки з вказаною датою виконання"""

    exec_date_str = args[0]
    try:
        exec_date = datetime.datetime.strptime(exec_date_str, '%Y-%m-%d').date()
    except ValueError:
        try:
            exec_date = datetime.datetime.strptime(exec_date_str, '%d.%m.%Y').date()
        except ValueError:
            raise DateIsNotValid

    if len(args) > 1:
        days = int(args[1])
    else:
        days = 0

    date1 = exec_date - datetime.timedelta(days=days)
    date2 = exec_date + datetime.timedelta(days=days)
    notes = session.query(Note).filter(and_(not_(Note.is_done), Note.execution_date >= date1,
                                            Note.execution_date <= date2)).order_by(Note.id).all()

    result = 'List of notes with date:\n'
    print_list = Paginator(notes).get_view(func=view_note)
    for item in print_list:
        if item is None:
            return 'No notes found'
        else:
            result += f'{item}'
    return result


@InputError
def find_tag(*args):
    """Повертає нотатки в яких є тег"""

    tag_find = args[0]
    notes = session.query(Note).join(Note.tags).filter(not_(Note.is_done)).filter(Tag.tag.ilike(tag_find)).order_by(Note.id).all()

    result = f'List of notes with tag "{tag_find}":\n'
    print_list = Paginator(notes).get_view(func=view_note)
    for item in print_list:
        if item is None:
            return 'No notes found'
        else:
            result += f'{item}'
    return result


def sort_by_tags(*args):
    notes = session.query(Note).join(Note.tags).filter(not_(Note.is_done)).order_by(Tag.tag).all()
    result = f'List of tag-sorted notes":\n'
    print_list = Paginator(notes).get_view(func=view_note)
    for item in print_list:
        if item is None:
            return 'No notes found'
        else:
            result += f'{item}'
    return result


def goodbye(*args):
    return 'You have finished working with notebook'


def unknown_command(*args):
    return 'Unknown command! Enter again!'


def help_me(*args):
    """Повертає допомогу по списку команд"""
    return """\nCommand format:
    help or ? - this help;
    add note <text> - add note;
    change note <id> <text> - change note;
    delete note <id> - delete note;
    add date <id> <date> - add/change date;
    add tag <id> <tag> - add tag;
    done <id> - mark note as done;
    return <id> - mark note as not done;
    show all - show all notes;
    show archived - show archived notes;
    show date <date> [<days>] - show notes by date +- days;
    find note <text> - find note by text;
    find tag <text> - find note by tag;
    sort by tags - show all notes sorted by tags;
    good bye or close or exit or . - exit the program"""


COMMANDS = {help_me: ['?', 'help'], goodbye: ['good bye', 'close', 'exit', '.'], add_note: ['add note '],
            add_date: ['add date '], show_all: ['show all'], show_archiv: ['show archived'],
            change_note: ['change note '], del_note: ['delete note '], find_note: ['find note '],
            show_date: ['show date '], done_note: ['done '], return_note: ['return '], add_tag: ["add tag"],
            find_tag: ["find tag"], sort_by_tags: ['sort by tags']}


def command_parser(user_command: str) -> (str, list):
    for key, list_value in COMMANDS.items():
        for value in list_value:
            if user_command.lower().startswith(value):
                args = user_command[len(value):].split()
                return key, args
    else:
        return unknown_command, []


def start_nb():
    print('\n\033[033mWelcome to notebook!\033[0m')
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
        command, data = command_parser(user_command)
        print(command(*data), '\n')
        if command is goodbye:
            break


Completer = NestedCompleter.from_nested_dict({'help': None, 'good bye': None, 'exit': None,
                                              'close': None, '?': None, '.': None,
                                              'add': {'note': None, 'date': None, 'tag': None},
                                              'show': {'all': None, 'archived': None, 'date': None},
                                              'change note': None, 'delete note': None,
                                              'find': {'note': None, 'tag': None}, 'done': None,
                                              'return': None, 'sort by tags': None})

if __name__ == '__main__':
    start_nb()
