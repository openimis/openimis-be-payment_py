import uuid

from core.rights_role_test_case import RightsRoleGraphQLTestCase
from core.test_helpers import (
    create_accountant_role,
    create_right_only_user,
    create_role_user,
)
from location.test_helpers import create_basic_test_locations


PAYMENTS_QUERY = """
query {
  payments(first: 5) {
    edges { node { id uuid } }
  }
}
"""


class PaymentRightsTests(RightsRoleGraphQLTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_basic_test_locations()

    def test_query_payments_right(self):
        allowed = create_right_only_user(
            "r_pay_q", ["gql_query_payments_perms"], district_codes=self.DISTRICT_CODES
        )
        denied = create_right_only_user("r_pay_q_no", [], district_codes=self.DISTRICT_CODES)
        self.assert_gql_ok(allowed, PAYMENTS_QUERY)
        self.assert_gql_unauthorized(denied, PAYMENTS_QUERY)

    def test_payment_mutation_rights_assigned(self):
        allowed = create_right_only_user(
            "r_pay_m",
            [
                "gql_mutation_create_payments_perms",
                "gql_mutation_update_payments_perms",
                "gql_mutation_delete_payments_perms",
            ],
            district_codes=self.DISTRICT_CODES,
        )
        denied = create_right_only_user("r_pay_m_no", [], district_codes=self.DISTRICT_CODES)
        for perm in (
            "gql_mutation_create_payments_perms",
            "gql_mutation_update_payments_perms",
            "gql_mutation_delete_payments_perms",
        ):
            self.assert_user_has_named_perms(allowed, [perm])
            self.assert_user_lacks_named_perms(denied, [perm])
        mid = str(uuid.uuid4())
        mutation = f"""
        mutation {{
          createPayment(input: {{
            clientMutationId: "{mid}"
            clientMutationLabel: "rights create payment"
          }}) {{ clientMutationId internalId }}
        }}
        """
        denied_user = denied
        self.assert_mutation_unauthorized(denied_user, mutation, mid)


class PaymentRoleTests(RightsRoleGraphQLTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_basic_test_locations()
        cls.accountant = create_role_user(
            "pay_acc", create_accountant_role(), district_codes=cls.DISTRICT_CODES
        )

    def test_accountant_can_query_and_mutate_payments(self):
        self.assert_user_has_named_perms(self.accountant, ["gql_query_payments_perms"])
        self.assert_user_has_named_perms(
            self.accountant, ["gql_mutation_create_payments_perms"]
        )
        self.assert_gql_ok(self.accountant, PAYMENTS_QUERY)
