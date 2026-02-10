class DuelError(Exception):
    """Base de toutes les erreurs liées aux duels."""


class DuelNotFound(DuelError):
    def __init__(self, duel_id: int):
        super().__init__(f"Le duel {duel_id} n'existe plus ou a expiré.")
        self.duel_id = duel_id

class DuelNotAcceptable(DuelError):
    def __init__(self, status: str):
        super().__init__(f"Le status {status} ne permet d'accepter ce duel.")
        self.status = status

class DuelNotFinishable(DuelError):
    def __init__(self, status: str):
        super().__init__(f"Le status {status} ne permet de finir ce duel.")
        self.status = status

class NotAuthorizedPlayer(DuelError):
    def __init__(self, user_id: int):
        super().__init__(f"Le joueur {user_id} n'a pas l'autorisation d'intéragir avec ce duel.")
        self.user_id = user_id

class InvalidStake(DuelError):
    def __init__(self, stake_xp: int):
        super().__init__(f"L'xp demandé n'est pas une option :{stake_xp}.")
        self.stake_xp = stake_xp

class InsufficientXp(DuelError):
    def __init__(self, required: int):
        super().__init__(f"Un des joueurs ne possède pas l'XP nécessaire. Requis : {required}.")
        self.required = required

class DuelAlreadyHandled(DuelError):
    def __init__(self, duel_id: int, expected_status: str):
        super().__init__(f"Duel {duel_id} n'est plus dans l'état attendu: {expected_status}.")
        self.duel_id = duel_id
        self.expected_status = expected_status

class SamePlayerDuel(DuelError):
    def __init__(self, player_a_id: int, player_b_id: int):
        super().__init__(f"Le duel ne peut pas avoir lieu entre 2 joueurs identiques. ({player_a_id} = {player_b_id})")
        self.player_a_id = player_a_id
        self.player_b_id = player_b_id

class PlayerAlreadyInDuel(DuelError):
    def __init__(self):
        super().__init__("Un joueur est déjà en duel")

class InvalidGameType(DuelError):
    def __init__(self, game_type: str):
        super().__init__(f"Le game_type demandé ({game_type}) n'est pas reconnu.")
        self.game_type = game_type

class MissingMessageId(DuelError):
    def __init__(self):
        super().__init__("Le message_id est manquant.")

class ConfigurationIncomplete(DuelError):
    def __init__(self):
        super().__init__("Le duel est mal configuré.")

class ConfigurationError(DuelError):
    def __init__(self):
        super().__init__("Un problème est survenu lors de la configuration.")

class InvalidResult(DuelError):
    def __init__(self, result: str):
        super().__init__(f"Le result demandé ({result}) n'est pas reconnu.")
        self.result = result

class DuelNotActive(DuelError):
    def __init__(self, status: str):
        super().__init__(f"Le status {status} ne permet de jouer dans ce duel.")
        self.status = status

class DuelNotFinished(DuelError):
    def __init__(self, duel_id: int, expected_status: str):
        super().__init__(f"Duel {duel_id} n'est plus dans l'état attendu: {expected_status}.")
        self.duel_id = duel_id
        self.expected_status = expected_status

class WrongGameType(DuelError):
    def __init__(self, game_type_received: str, game_type_expected: str):
        super().__init__(f"Le game_type reçu ({game_type_received}) ne correspond pas au game_type attendu ({game_type_expected}).")
        self.game_type_received = game_type_received
        self.game_type_expected = game_type_expected

class InvalidMove(DuelError):
    def __init__(self):
        super().__init__("Le coup joué n'est pas un coup valide.")

class AlreadyPlayed(DuelError):
    def __init__(self):
        super().__init__("Le joueur a déjà joué.")

class PayloadError(DuelError):
    def __init__(self):
        super().__init__("Erreur lors de la persistance du payload.")

class ExpiredDuel(DuelError):
    def __init__(self, duel_id: int):
        super().__init__(f"Le duel ({duel_id}) est expiré.")
        self.duel_id = duel_id