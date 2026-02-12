from unittest import mock

from core.models.openimis_graphql_test_case import openIMISGraphQLTestCase, BaseTestContext
from core.test_helpers import create_test_interactive_user
from payment import schema as payment_schema
from graphene import Schema


class QueryTestContract(openIMISGraphQLTestCase):
    # This is required by some version of graphene but is never used. It should be set to the schema but the import
    # is shown as an error in the IDE, so leaving it as True.
    GRAPHQL_SCHEMA = True
    admin_user = None
    schema = Schema(
        query=payment_schema.Query,
    )

    class AnonymousUserContext:
        user = mock.Mock(is_anonymous=True)

    @classmethod
    def setUpClass(cls):
        super(QueryTestContract, cls).setUpClass()
        cls.user = create_test_interactive_user(username='PaymentAdmin')
        # some test data so as to created contract properly
        cls.user_token = BaseTestContext(user=cls.user).get_jwt()

    def test_query_payment_additionnal_filter(self):
        response = self.query(
            """
    query {
      payments(additionalFilter: "{\\"contract\\":\\"5b358ead-f2fb-4acf-ba90-3c1c74e0bf01\\"}",first: 10,orderBy: ["-receivedDate"])
      {
        totalCount

    pageInfo { hasNextPage, hasPreviousPage, startCursor, endCursor}
    edges
    {
      node
      {
        uuid,id,requestDate,expectedAmount,receivedDate,receivedAmount,status,receiptNo,typeOfPayment,clientMutationId,validityTo
      }
    }
      }
    }
    """,
            headers={"HTTP_AUTHORIZATION": f"Bearer {self.user_token}"})
        self.assertResponseNoErrors(response)
