from dataclasses import dataclass

from eldoria.features.duel.duel_service import DuelService
from eldoria.features.temp_voice.temp_voice_service import TempVoiceService
from eldoria.features.xp.xp_service import XpService


@dataclass(slots=True) 
class Services: 
    duel: DuelService
    temp_voice:TempVoiceService
    xp: XpService