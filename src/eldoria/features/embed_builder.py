"""Point d'entrée unique pour générer les embeds.

Ce module re-exporte les fonctions des sous-modules d'embed.
Les imports sont relatifs pour fonctionner quand le bot est lancé
comme package (src/eldoria/...).
"""

from .embed.help_embed import *
from .embed.roles_embed import *
from .embed.temp_voice_embed import *
from .embed.xp_embed import *
from .embed.welcome_embed import *
from .embed.version_embed import *

from .embed.common.embedImages import *
