from dataclasses import dataclass

from eldoria.features.duel.duel_service import DuelService


@dataclass(slots=True) 
class Services: 
    duel: DuelService