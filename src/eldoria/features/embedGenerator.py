"""Point d'entrée unique pour générer les embeds.

Ce module re-exporte les fonctions des sous-modules d'embed.
Les imports sont relatifs pour fonctionner quand le bot est lancé
comme package (src/eldoria/...).
"""

from .embed.helpEmbed import *
from .embed.rolesEmbed import *
from .embed.tempVoiceEmbed import *
from .embed.xpEmbed import *
from .embed.welcomeEmbed import *

from .embed.common.embedImages import *
