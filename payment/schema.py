from django.db.models import Q
from django.core.exceptions import PermissionDenied
import graphene_django_optimizer as gql_optimizer

from .apps import PaymentConfig
from django.utils.translation import gettext as _
from core.schema import signal_mutation_module_before_mutating, OrderedDjangoFilterConnectionField, filter_validity
from core.services import wait_for_mutation
from contribution import models as contribution_models
from .models import Payment, PaymentDetail
# We do need all queries and mutations in the namespace here.
from .gql_queries import graphene, PaymentGQLType, PaymentDetailGQLType
from .gql_mutations import (
    CreatePaymentMutation,
    UpdatePaymentMutation,
    DeletePaymentsMutation,
    on_policy_mutation,
    on_payment_mutation,
)
from .signals import signal_before_payment_query, _read_signal_results


class Query(graphene.ObjectType):
    payments = OrderedDjangoFilterConnectionField(
        PaymentGQLType,
        show_history=graphene.Boolean(),
        show_reconciled=graphene.Boolean(),
        client_mutation_id=graphene.String(),
        orderBy=graphene.List(of_type=graphene.String),
        # OFS-257: Create dynamic filters for the payment mutation
        additional_filter=graphene.JSONString(),
    )
    payment_details = OrderedDjangoFilterConnectionField(
        PaymentDetailGQLType,
        orderBy=graphene.List(of_type=graphene.String),
    )
    payments_by_premiums = OrderedDjangoFilterConnectionField(
        PaymentGQLType,
        premium_uuids=graphene.List(graphene.String, required=True),
        orderBy=graphene.List(of_type=graphene.String),
    )

    def resolve_payments(self, info, **kwargs):
        if not info.context.user.has_perms(PaymentConfig.gql_query_payments_perms):
            raise PermissionDenied(_("unauthorized"))
        filters = []
        # OFS-257: Create dynamic filters for the payment mutation
        additional_filter = kwargs.get('additional_filter', None)
        # go to process additional filter only when this arg of filter was passed into query
        if additional_filter:
            filters_from_signal = _get_additional_filter(
                sender=Payment, additional_filter=additional_filter, user=info.context.user
            )
            # check if there is filter from signal (perms will be checked in the signals)
            if len(filters_from_signal) == 0:
                raise PermissionDenied(_("unauthorized"))
            filters.extend(filters_from_signal)
        if not info.context.user.has_perms(PaymentConfig.gql_query_payments_perms):
            raise PermissionDenied(_("unauthorized"))
        client_mutation_id = kwargs.get("client_mutation_id", None)
        if client_mutation_id:
            wait_for_mutation(client_mutation_id)
            filters.append(
                Q(mutations__mutation__client_mutation_id=client_mutation_id))
        show_history = kwargs.get('show_history', False)
        if not show_history and not kwargs.get('uuid', None):
            filters += filter_validity(**kwargs)
        show_reconciled = kwargs.get('show_reconciled', False)
        if show_reconciled:
            filters.append(
                Q(reconciliation_date__isnull=False)
            )

        return gql_optimizer.query(Payment.objects.filter(*filters).distinct().all(), info)

    def resolve_payment_details(self, info, **kwargs):
        if not info.context.user.has_perms(PaymentConfig.gql_query_payments_perms):
            raise PermissionDenied(_("unauthorized"))
        pass

    def resolve_payments_by_premiums(self, info, **kwargs):
        if not info.context.user.has_perms(PaymentConfig.gql_query_payments_perms):
            raise PermissionDenied(_("unauthorized"))
        premiums = contribution_models.Premium.objects.values_list(
            'id').filter(Q(uuid__in=kwargs.get('premium_uuids')))
        detail_ids = PaymentDetail.objects.values_list('payment_id').filter(Q(premium_id__in=premiums),
                                                                            *PaymentDetail.filter_validity(**kwargs)).distinct()
        return Payment.objects.filter(Q(id__in=detail_ids))


class Mutation(graphene.ObjectType):
    create_payment = CreatePaymentMutation.Field()
    update_payment = UpdatePaymentMutation.Field()
    delete_payment = DeletePaymentsMutation.Field()


def bind_signals():
    signal_mutation_module_before_mutating["policy"].connect(on_policy_mutation)
    signal_mutation_module_before_mutating["payment"].connect(on_payment_mutation)


def _get_additional_filter(sender, additional_filter, user):
    # function to retrieve additional filters from signal
    filters_from_signal = []
    if additional_filter:
        # send signal to append additional filter
        results_signal = signal_before_payment_query.send(
            sender=sender, additional_filter=additional_filter, user=user,
        )
        filters_from_signal = _read_signal_results(results_signal)
    return filters_from_signal
