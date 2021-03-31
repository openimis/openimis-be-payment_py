from django.db.models import Q
from django.core.exceptions import PermissionDenied
from graphene_django.filter import DjangoFilterConnectionField
import graphene_django_optimizer as gql_optimizer
from payment.services import detach_payment_detail

from .apps import PaymentConfig
from django.utils.translation import gettext as _
from core.schema import signal_mutation_module_before_mutating, OrderedDjangoFilterConnectionField, filter_validity
from contribution import models as contribution_models
from .models import Payment, PaymentDetail
# We do need all queries and mutations in the namespace here.
from .gql_queries import *  # lgtm [py/polluting-import]
from .gql_mutations import *  # lgtm [py/polluting-import]
from .signals import signal_before_payment_query


class Query(graphene.ObjectType):
    payments = OrderedDjangoFilterConnectionField(
        PaymentGQLType,
        show_history=graphene.Boolean(),
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
        client_mutation_id = kwargs.get("client_mutation_id", None)
        if client_mutation_id:
            filters.append(Q(mutations__mutation__client_mutation_id=client_mutation_id))
        show_history = kwargs.get('show_history', False)
        if not show_history and not kwargs.get('uuid', None):
            filters += filter_validity(**kwargs)
        # OFS-257: Create dynamic filters for the payment mutation
        additional_filter = kwargs.get('additional_filter', None)
        if additional_filter:
            # send signal to append additional filter
            signal_before_payment_query.send(
                sender=self, additional_filter=additional_filter, filters=filters, user=info.context.user,
            )
            # distinct query result after filtering via Policy Holder
            return gql_optimizer.query(Payment.objects.filter(*filters).distinct().all(), info)
        return gql_optimizer.query(Payment.objects.filter(*filters).all(), info)

    def resolve_payment_details(self, info, **kwargs):
        if not info.context.user.has_perms(PaymentConfig.gql_query_payments_perms):
            raise PermissionDenied(_("unauthorized"))
        pass

    def resolve_payments_by_premiums(self, info, **kwargs):
        if not info.context.user.has_perms(PaymentConfig.gql_query_payments_perms):
            raise PermissionDenied(_("unauthorized"))
        premiums = contribution_models.Premium.objects.values_list('id').filter(Q(uuid__in=kwargs.get('premium_uuids')))
        detail_ids = PaymentDetail.objects.values_list('payment_id').filter(Q(premium_id__in=premiums),
                                                                            *filter_validity(**kwargs)).distinct()
        return Payment.objects.filter(Q(id__in=detail_ids))


class Mutation(graphene.ObjectType):
    create_payment = CreatePaymentMutation.Field()
    update_payment = UpdatePaymentMutation.Field()
    delete_payment = DeletePaymentsMutation.Field()


def bind_signals():
    signal_mutation_module_before_mutating["policy"].connect(on_policy_mutation)
    signal_mutation_module_before_mutating["payment"].connect(on_payment_mutation)
