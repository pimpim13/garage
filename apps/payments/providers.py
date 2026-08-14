from abc import ABC, abstractmethod


class PaymentProvider(ABC):
    """Point d'extension pour un futur prestataire de paiement en ligne (Stripe, etc.)."""

    @abstractmethod
    def marquer_paye(self, achat, **kwargs):
        """Marque un Achat comme payé et renvoie les métadonnées de la transaction."""


class ManualPaymentProvider(PaymentProvider):
    """Paiement saisi à la main par un gestionnaire/admin, en attendant un vrai prestataire."""

    def marquer_paye(self, achat, **kwargs):
        achat.statut_paiement = achat.StatutPaiement.PAYE
        achat.save(update_fields=['statut_paiement'])
        return {}
