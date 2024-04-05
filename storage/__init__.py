from .firestore import complete
from .firestore import delete
from .firestore import list_files
from .firestore import get_file
from .firestore import get_logs
from .firestore import log
from .firestore import get_edits
from .firestore import add_edit
from .firestore import forget
from .firestore import new
from .firestore import save
from .firestore import share
from .firestore import login
from .firestore import register
from .firestore import reset_password
from .firestore import reset_password_with_code
from .firestore import confirm
from .firestore import get_users
from .firestore import get_email
from .firestore import get_history

def set_logger(logger):
    firestore.set_logger(logger)
