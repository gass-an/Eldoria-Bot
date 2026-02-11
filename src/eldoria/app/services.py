"""Module définissant les services utilisés par le bot Eldoria, regroupant les différentes fonctionnalités en un seul endroit pour une gestion centralisée."""

from dataclasses import dataclass, fields

from eldoria.features.duel.duel_service import DuelService
from eldoria.features.role.role_service import RoleService
from eldoria.features.save.save_service import SaveService
from eldoria.features.temp_voice.temp_voice_service import TempVoiceService
from eldoria.features.welcome.welcome_service import WelcomeService
from eldoria.features.xp.xp_service import XpService


@dataclass(slots=True) 
class Services: 
    """Classe regroupant les différents services utilisés par le bot Eldoria, facilitant l'accès et la gestion de ces fonctionnalités."""

    duel: DuelService
    role: RoleService
    save: SaveService
    temp_voice: TempVoiceService
    welcome: WelcomeService
    xp: XpService

    def __len__(self) -> int:
        """Retourne le nombre de services définis dans cette classe."""
        return len(fields(self))