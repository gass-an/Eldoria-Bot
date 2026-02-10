from dataclasses import dataclass

from eldoria.features.duel.duel_service import DuelService
from eldoria.features.xp.xp_service import XpService


@dataclass(slots=True) 
class Services: 
    duel: DuelService
    xp: XpService