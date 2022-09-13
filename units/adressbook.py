import datetime
import re

from prompt_toolkit import prompt
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.history import FileHistory

from units.command_parser import command_parser, RainbowLexer
from units.paginator import Paginator, hyphenation_string

from src.db import session
from src.models import Contact, Phone, Email
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlalchemy import and_, not_, or_


class PhoneUserAlreadyExists(Exception):
    """You cannot add an existing phone number to a user"""


class EmailUserAlreadyExists(Exception):
    """You cannot add an existing email to a user"""


class DateIsNotValid(Exception):
    """You cannot add an invalid date"""


class EmailIsNotValid(Exception):
    """Email is not valid, try again"""


class FindNotFound(Exception):
    """Find is not valid, try again"""


class InputError:
    def __init__(self, func) -> None:
        self.func = func

    def __call__(self, contacts, *args):
        try:
            return self.func(contacts, *args)
        except IndexError:
            return 'Error! Give me name and phone or birthday please!'
        except KeyError:
            return 'Error! User not found!'
        except ValueError:
            return 'Error! Phone number is incorrect!'
        except PhoneUserAlreadyExists:
            return 'Error! You cannot add an existing phone number to a user'
        except EmailUserAlreadyExists:
            return 'Error! You cannot add an existing email to a user'
        except DateIsNotValid:
            return 'Error! Date is not valid'
        except AttributeError:
            return 'Error! Email is not valid'
        except FindNotFound:
            return 'Error! Try command find or search "words" that find contact'
        except NoResultFound:
            return 'Error! Input data are not exist!'
        except IntegrityError:
            session.close()
            return 'Error! Output data are now exist!'


def phone_normalizer(phone: str):
    def is_code_valid(phone_code: str) -> bool:
        if phone_code[:2] in ('03', '04', '05', '06', '09') and phone_code[2] != '0' and phone_code != '039':
            return True
        return False

    result = None
    phone = phone.removeprefix('+').replace('(', '').replace(')', '').replace('-', '')
    if phone.isdigit():
        if phone.startswith('0') and len(phone) == 10 and is_code_valid(phone[:3]):
            result = '+38' + phone
        if phone.startswith('380') and len(phone) == 12 and is_code_valid(phone[2:5]):
            result = '+' + phone
        if 10 <= len(phone) <= 14 and not phone.startswith('0') and not phone.startswith('380'):
            result = '+' + phone
    return result


def is_valid_email(mail_):
    get_emails = re.findall(r'\b(?:[a-z0-9_-]+[\.])*[a-z0-9_-]+@[a-z0-9_-]+(?:\.[a-z0-9_-]+)*\.[a-z]{2,}', mail_.lower())
    if not get_emails:
        raise AttributeError(f"Неправильний тип значення {mail_}")
    return get_emails


def view_contact(contact):
    id_ = contact.id
    name_ = contact.name
    birthday_ = datetime.date.strftime(contact.birthday, '%d %b %Y') if contact.birthday else '     -    '
    address_ = contact.address
    phone_db = session.query(Phone).filter(Phone.contact_id == id_).order_by(Phone.phone_number).all()
    email_db = session.query(Email).filter(Email.contact_id == id_).order_by(Email.mail).all()
    phones_str = ', '.join([ph.phone_number for ph in phone_db])
    emails_str = ', '.join([em.mail for em in email_db])
    return f'\033[34mContact\033[0m \033[35m{name_:50}\033[0m \033[34mBirthday:\033[0m {birthday_}\n' + \
        hyphenation_string(f'\033[34mPhones:\033[0m {phones_str}') + '\n' + \
        hyphenation_string(f'\033[34mEmail:\033[0m {emails_str}') + '\n' + \
        hyphenation_string(f'\033[34mAddress:\033[0m {address_ if not address_ is None else " - "}')


@InputError
def add_contact(*args):
    add_name = args[0]
    if len(args) == 1:
        try:
            session.query(Contact).filter(Contact.name == add_name).one()
            return f'Contact {add_name} now exist!'
        except NoResultFound:
            new_contact = Contact(name=add_name)
            session.add(new_contact)
            session.commit()
            return f'Add contact {add_name} without phones'

    add_phone = phone_normalizer(args[1])
    try:
        session.query(Phone).filter(Phone.phone_number == add_phone).one()
        return f'Phone {add_phone} now exist'
    except NoResultFound:
        try:
            contact = session.query(Contact).filter(Contact.name == add_name).one()
        except NoResultFound:
            new_contact = Contact(name=add_name)
            session.add(new_contact)
            session.commit()
            contact = session.query(Contact).filter(Contact.name == add_name).one()
        phone = Phone(phone_number=add_phone, contact_id=contact.id)
        session.add(phone)
        session.commit()
    return f'Add contact {add_name} with phone number {add_phone}'


def salute(*args):
    return 'Hello! How can I help you?'


@InputError
def change_contact(*args):
    name_, old_phone, new_phone = args[0], phone_normalizer(args[1]), phone_normalizer(args[2])
    if old_phone is None:
        return 'Error! Old phone number is incorrect!'
    if new_phone is None:
        return 'Error! New phone number is incorrect!'
    contact = session.query(Contact).filter(Contact.name == name_).one()
    phone = session.query(Phone).filter(and_(Phone.phone_number == old_phone, Phone.contact_id == contact.id)).one()
    phone.phone_number = new_phone
    session.commit()
    return f'Change to contact {name_} phone number from {old_phone} to {new_phone}'


@InputError
def show_phone(*args):
    name_ = args[0]
    contact = session.query(Contact).filter(Contact.name == name_).one()
    return view_contact(contact)


@InputError
def del_phone(*args):
    name_, phone_ = args[0], phone_normalizer(args[1])
    if phone_ is None:
        return 'Error! Phone number is incorrect!'
    contact = session.query(Contact).filter(Contact.name == name_).one()
    phone = session.query(Phone).filter(and_(Phone.contact_id == contact.id, Phone.phone_number == phone_)).one()
    session.delete(phone)
    session.commit()
    return f'Delete phone {phone_} from contact {name_}'


def show_all(*args):
    contacts = session.query(Contact).order_by(Contact.name).all()
    result = 'List of all users:\n'
    print_list = Paginator(contacts).get_view(func=view_contact)
    for item in print_list:
        if item is None:
            return 'No contacts found'
        else:
            result += f'{item}'
    return result


@InputError
def add_birthday(*args):
    name_, birthday_str = args[0], args[1]
    contact = session.query(Contact).filter(Contact.name == name_).one()  # перевірка на існування
    try:
        birthday_ = datetime.datetime.strptime(birthday_str, '%Y-%m-%d').date()
    except ValueError:
        try:
            birthday_ = datetime.datetime.strptime(birthday_str, '%d.%m.%Y').date()
        except ValueError:
            raise DateIsNotValid
    contact.birthday = birthday_
    session.commit()
    return f'Birthday {birthday_} added/modify to contact {name_}'


@InputError
def days_to_user_birthday(*args):
    name_ = args[0]
    contact = session.query(Contact).filter(Contact.name == name_).one()  # перевірка на існування
    if contact.birthday is None:
        return 'Contact {name_} has no birthday'
    return f'{(contact.days_to_birthday)} days to birthday contact {contact.name}'


@InputError
def show_birthday(*args):
    days = int(args[0])
    contacts = session.query(Contact).filter(Contact.birthday != None).order_by(Contact.name).all()
    result = 'List of all users:\n'
    print_list = Paginator([c for c in contacts if c.days_to_birthday <= days]).get_view(func=view_contact)
    for item in print_list:
        if item is None:
            return 'No contacts found'
        else:
            result += f'{item}'
    return result


def goodbye(*args):
    return 'You have finished working with addressbook'


@InputError
def search(*args):
    if len(args) == 1:
        substr = args[0]
        contacts = session.query(Contact).outerjoin(Phone).outerjoin(Email).filter(or_(Contact.name.ilike(f'%{substr}%'),
                Phone.phone_number.ilike(f'%{substr}%'), Email.mail.ilike(f'%{substr}%'))).order_by(Contact.name).all()

        result = f'List of users with \'{substr.lower()}\' in data:\n'
        print_list = Paginator(contacts).get_view(func=view_contact)
        for item in print_list:
            if item is None:
                return f'Users with \'{substr.lower()}\' in data not found'
            else:
                result += f'{item}'
        return result
    else:
        raise FindNotFound


@InputError
def del_user(*args):
    name_ = args[0]
    session.query(Contact).filter(Contact.name == name_).one()
    yes_no = input(f'Are you sure you want to delete the user {name_}? (Y/n) ')
    if yes_no == 'Y':
        session.query(Contact).filter(Contact.name == name_).delete()
        session.commit()
        return f'Delete contact {name_}'
    else:
        return 'Contact not deleted'


@InputError
def add_email(*args):
    name_, emails_ = args[0], args[1]
    contact = session.query(Contact).filter(Contact.name == name_).one()  # перевірка на існування
    emails_ = is_valid_email(emails_)
    # Додавання нових адрес
    result_emails = []
    for email_ in emails_:
        new_email = Email(contact_id=contact.id, mail=email_)
        try:
            session.add(new_email)
            session.commit()
            result_emails.append(email_)
        except:
            print(f'{email_} exist')
            session.close()
    if result_emails:
        return f'Email(s) {", ".join(result_emails)} add to contact {name_}'
    else:
        return f'No Emails added to contact {name_}'


@InputError
def del_email(*args):
    name_, email_ = args[0], args[1].lower()
    contact = session.query(Contact).filter(Contact.name == name_).one()
    email_del = session.query(Email).filter(and_(Email.contact_id == contact.id, Email.mail == email_)).one()
    session.delete(email_del)
    session.commit()
    return f'Delete email {email_} from contact {name_}'


@InputError
def add_address(*args):
    name_, address_ = args[0], " ".join(args[1:])
    contact = session.query(Contact).filter(Contact.name == name_).one()
    contact.address = address_.strip()
    session.commit()
    return f'Add/modify address {address_} to contact {name_}'


def help_me(*args):
    return """\nCommand format:
    help or ? - this help;
    hello - greeting;
    add <name> [<phone>] - add contact to adressbook;
    change <name> <old_phone> <new_phone> - change the contact's phone number;
    del phone <name> <phone> - delete the contact's phone number;
    delete <name> - delete the contact;
    birthday <name> <birthday> - add/modify the contact's birthday;
    email <name> <email> - add the contact's email;
    del email <name> <email> - delete the contact's email;
    address <name> <address> - add/modify the contact's address;
    show <name> - show the contact's data;
    show all - show data of all contacts;
    find or search <sub> - show data of all contacts with sub in name, phones or emails;
    days to birthday <name> - show how many days to the contact's birthday;
    show birthday days <N> - show the contact's birthday in the next N days;
    good bye or close or exit or . - exit the program"""


COMMANDS_A = {salute: ['hello'], add_contact: ['add '], change_contact: ['change '], help_me: ['?', 'help'],
              show_all: {'show all'}, goodbye: ['good bye', 'close', 'exit', '.'], del_phone: ['del phone '],
              add_birthday: ['birthday'], days_to_user_birthday: ['days to birthday '],
              show_birthday: ['show birthday days '], show_phone: ['show '], search: ['find ', 'search '],
              del_user: ['delete '], add_email: ['email '], add_address: ['address'], del_email: ['del email']}


def start_ab():
    print('\n\033[033mWelcome to the address book!\033[0m')
    print(f"\033[032mType command or '?' for help \033[0m\n")
    while True:
        with open("history.txt", "wb"):
            pass
        # user_command = input('Enter command >>> ')
        user_command = prompt('Enter command >>> ',
                              history=FileHistory('history.txt'),
                              auto_suggest=AutoSuggestFromHistory(),
                              completer=Completer,
                              lexer=RainbowLexer()
                              )
        command, data = command_parser(user_command, COMMANDS_A)
        print(command(*data), '\n')
        if command is goodbye:
            break


Completer = NestedCompleter.from_nested_dict({'help': None, 'hello': None, 'good bye': None, 'exit': None,
                                              'close': None, '?': None, '.': None, 'birthday': None,
                                              'days to birthday': None, 'add': None,
                                              'show': {'all': None, 'birthday days': None},
                                              'change': None, 'del': {'phone': None, 'email': None}, 'delete': None,
                                              'clear': None, 'email': None, 'find': None, 'search': None,
                                              'address': None})

if __name__ == "__main__":
    start_ab()
