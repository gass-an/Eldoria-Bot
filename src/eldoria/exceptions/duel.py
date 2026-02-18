"""Module de définition des exceptions personnalisées liées aux duels dans Eldoria Bot."""

from eldoria.exceptions.base import AppError


class DuelError(AppError):
    """Base de toutes les erreurs liées aux duels."""

# ---------------- internal errors ----------------
class DuelRepositoryError(DuelError):
    """Erreur technique liée à la persistance des duels."""

class DuelInsertFailed(DuelRepositoryError):
    """Impossible de récupérer l'ID du duel après insertion."""

    def __init__(self) -> None:
        """Initialise l'exception avec un message indiquant l'échec de la récupération de l'ID du duel."""
        super().__init__("Duel inséré mais impossible de récupérer son ID.")


# ---------------- exceptions métier ----------------
class DuelNotFound(DuelError):
    """Exception levée lorsqu'un duel n'est pas trouvé dans la base de données, ou a expiré."""

    def __init__(self, duel_id: int) -> None:
        """Initialise l'exception avec l'identifiant du duel concerné."""
        super().__init__(f"Le duel {duel_id} n'existe plus ou a expiré.")
        self.duel_id = duel_id

class DuelNotAcceptable(DuelError):
    """Exception levée lorsqu'un duel n'est pas dans un état permettant de l'accepter."""

    def __init__(self, status: str) -> None:
        """Initialise l'exception avec le status du duel qui empêche de l'accepter."""
        super().__init__(f"Le status {status} ne permet d'accepter ce duel.")
        self.status = status

class DuelNotFinishable(DuelError):
    """Exception levée lorsqu'un duel n'est pas dans un état permettant de le terminer."""

    def __init__(self, status: str) -> None:
        """Initialise l'exception avec le status du duel qui empêche de le terminer."""
        super().__init__(f"Le status {status} ne permet de finir ce duel.")
        self.status = status

class NotAuthorizedPlayer(DuelError):
    """Exception levée lorsqu'un joueur tente d'interagir avec un duel sans en être un participant."""

    def __init__(self, user_id: int) -> None:
        """Initialise l'exception avec l'identifiant de l'utilisateur non autorisé."""
        super().__init__(f"Le joueur {user_id} n'a pas l'autorisation d'intéragir avec ce duel.")
        self.user_id = user_id

class InvalidStake(DuelError):
    """Exception levée lorsqu'une mise (stake) proposée pour un duel n'est pas valide."""

    def __init__(self, stake_xp: int) -> None:
        """Initialise l'exception avec la valeur de mise invalide."""
        super().__init__(f"L'xp demandé n'est pas une option :{stake_xp}.")
        self.stake_xp = stake_xp

class InsufficientXp(DuelError):
    """Exception levée lorsqu'un des joueurs ne possède pas l'XP nécessaire pour la mise d'un duel."""

    def __init__(self, required: int) -> None:
        """Initialise l'exception avec la quantité d'XP requise pour la mise."""
        super().__init__(f"Un des joueurs ne possède pas l'XP nécessaire. Requis : {required}.")
        self.required = required

class DuelAlreadyHandled(DuelError):
    """Exception levée lorsqu'une action est tentée sur un duel qui a déjà été traité (ex: quelqu'un a cliqué juste avant)."""

    def __init__(self, duel_id: int, expected_status: str) -> None:
        """Initialise l'exception avec l'identifiant du duel concerné et le status attendu qui n'est plus valide."""
        super().__init__(f"Duel {duel_id} n'est plus dans l'état attendu: {expected_status}.")
        self.duel_id = duel_id
        self.expected_status = expected_status

class SamePlayerDuel(DuelError):
    """Exception levée lorsqu'un duel est tenté entre un joueur et lui-même."""

    def __init__(self, player_a_id: int, player_b_id: int) -> None:
        """Initialise l'exception avec les identifiants des deux joueurs impliqués dans le duel."""
        super().__init__(f"Le duel ne peut pas avoir lieu entre 2 joueurs identiques. ({player_a_id} = {player_b_id})")
        self.player_a_id = player_a_id
        self.player_b_id = player_b_id

class PlayerAlreadyInDuel(DuelError):
    """Exception levée lorsqu'un duel est tenté alors qu'un des joueurs est déjà impliqué dans un autre duel actif."""

    def __init__(self) -> None:
        """Initialise l'exception sans attributs supplémentaires, car le message d'erreur est générique."""
        super().__init__("Un joueur est déjà en duel")

class InvalidGameType(DuelError):
    """Exception levée lorsqu'un type de jeu spécifié pour un duel n'est pas reconnu."""

    def __init__(self, game_type: str) -> None:
        """Initialise l'exception avec le type de jeu invalide qui a été spécifié."""
        super().__init__(f"Le game_type demandé ({game_type}) n'est pas reconnu.")
        self.game_type = game_type

class MissingMessageId(DuelError):
    """Exception levée lorsqu'une action nécessitant un message_id associé à un duel est tentée alors que le message_id est manquant (ex: duel pas encore configuré)."""

    def __init__(self) -> None:
        """Initialise l'exception sans attributs supplémentaires, car le message d'erreur est générique."""
        super().__init__("Le message_id est manquant.")

class ConfigurationIncomplete(DuelError):
    """Exception levée lorsqu'une action nécessitant une configuration complète du duel est tentée alors que la configuration est incomplète (ex: game_type ou stake_xp manquants)."""

    def __init__(self) -> None:
        """Initialise l'exception sans attributs supplémentaires, car le message d'erreur est générique."""
        super().__init__("Le duel est mal configuré.")

class ConfigurationError(DuelError):
    """Exception levée lorsqu'une erreur technique survient lors de la configuration du duel (ex: problème de persistance du payload)."""

    def __init__(self) -> None:
        """Initialise l'exception sans attributs supplémentaires, car le message d'erreur est générique."""
        super().__init__("Un problème est survenu lors de la configuration.")

class InvalidResult(DuelError):
    """Exception levée lorsqu'un résultat de duel spécifié n'est pas reconnu ou valide."""

    def __init__(self, result: str) -> None:
        """Initialise l'exception avec le résultat invalide qui a été spécifié."""
        super().__init__(f"Le result demandé ({result}) n'est pas reconnu.")
        self.result = result

class DuelNotActive(DuelError):
    """Exception levée lorsqu'une action nécessitant que le duel soit actif est tentée alors que le duel n'est pas dans un état actif."""

    def __init__(self, status: str) -> None:
        """Initialise l'exception avec le status du duel qui empêche l'action nécessitant un duel actif."""
        super().__init__(f"Le status {status} ne permet de jouer dans ce duel.")
        self.status = status

class DuelNotFinished(DuelError):
    """Exception levée lorsqu'une action nécessitant que le duel soit terminé est tentée alors que le duel n'est pas dans un état terminé."""

    def __init__(self, duel_id: int, expected_status: str) -> None:
        """Initialise l'exception avec l'identifiant du duel concerné et le status attendu qui n'est plus valide pour une action nécessitant un duel terminé."""
        super().__init__(f"Duel {duel_id} n'est plus dans l'état attendu: {expected_status}.")
        self.duel_id = duel_id
        self.expected_status = expected_status

class WrongGameType(DuelError):
    """Exception levée lorsqu'une action spécifique à un type de jeu est tentée alors que le duel n'est pas configuré avec ce type de jeu."""

    def __init__(self, game_type_received: str, game_type_expected: str) -> None:
        """Initialise l'exception avec le type de jeu reçu qui ne correspond pas au type de jeu attendu pour l'action tentée."""
        super().__init__(f"Le game_type reçu ({game_type_received}) ne correspond pas au game_type attendu ({game_type_expected}).")
        self.game_type_received = game_type_received
        self.game_type_expected = game_type_expected

class InvalidMove(DuelError):
    """Exception levée lorsqu'un coup joué dans un duel n'est pas valide selon les règles du jeu configuré."""

    def __init__(self) -> None:
        """Initialise l'exception sans attributs supplémentaires, car le message d'erreur est générique."""
        super().__init__("Le coup joué n'est pas un coup valide.")

class AlreadyPlayed(DuelError):
    """Exception levée lorsqu'un joueur tente de jouer un coup alors qu'il a déjà joué dans ce duel."""

    def __init__(self) -> None:
        """Initialise l'exception sans attributs supplémentaires, car le message d'erreur est générique."""
        super().__init__("Le joueur a déjà joué.")

class PayloadError(DuelError):
    """Exception levée lorsqu'une erreur survient lors de la manipulation du payload d'un duel (ex: problème de sérialisation/désérialisation, données manquantes ou corrompues)."""

    def __init__(self) -> None:
        """Initialise l'exception sans attributs supplémentaires, car le message d'erreur est générique."""
        super().__init__("Erreur lors de la persistance du payload.")

class ExpiredDuel(DuelError):
    """Exception levée lorsqu'une action est tentée sur un duel qui a expiré (ex: délai d'acceptation dépassé)."""

    def __init__(self, duel_id: int) -> None:
        """Exception levée lorsqu'une action est tentée sur un duel qui a expiré."""
        super().__init__(f"Le duel ({duel_id}) est expiré.")
        self.duel_id = duel_id

class InvalidSnapshot(DuelError):
    """Snapshot de duel invalide ou incomplet."""

    def __init__(self) -> None:
        """Initialise l'exception sans attributs supplémentaires, car le message d'erreur est générique."""
        super().__init__("Le snapshot de duel est invalide ou incomplet.")