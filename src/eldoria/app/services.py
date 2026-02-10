from dataclasses import dataclass

from eldoria.features.duel.duel_service import DuelService
from eldoria.features.role.role_service import RoleService
from eldoria.features.save.save_service import SaveService
from eldoria.features.temp_voice.temp_voice_service import TempVoiceService
from eldoria.features.welcome.welcome_service import WelcomeService
from eldoria.features.xp.xp_service import XpService


@dataclass(slots=True) 
class Services: 
    duel: DuelService
    role: RoleService
    save: SaveService
    temp_voice: TempVoiceService
    welcome: WelcomeService
    xp: XpService