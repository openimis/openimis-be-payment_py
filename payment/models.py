import uuid

from core import fields
from core import models as core_models
from django.db import models
from contribution.models import Premium
from django.utils.translation import gettext_lazy as _


class Payment(core_models.VersionedModel):
    STATUS_REJECTEDPOSTED_3 = -3
    STATUS_REJECTEDPOSTED_2 = -2
    STATUS_REJECTEDPOSTED_1 = -1
    STATUS_NOTYETCONFIRMED = 1
    STATUS_POSTED = 2
    STATUS_ASSIGNED = 3
    STATUS_UNMATCHED = 4
    STATUS_PAYMENTMATCHED = 5
    STATUS_CHOICES = (
        (STATUS_REJECTEDPOSTED_3, _("REJECTEDPOSTED_3")),
        (STATUS_REJECTEDPOSTED_2, _("REJECTEDPOSTED_2")),
        (STATUS_REJECTEDPOSTED_1, _("REJECTEDPOSTED_1")),
        (STATUS_NOTYETCONFIRMED, _("NOTYETCONFIRMED")),
        (STATUS_POSTED, _("POSTED")),
        (STATUS_ASSIGNED, _("ASSIGNED")),
        (STATUS_UNMATCHED, _("UNMATCHED")),
        (STATUS_PAYMENTMATCHED, _("PAYMENTMATCHED")),
    )

    id = models.BigAutoField(db_column='PaymentID', primary_key=True)
    uuid = models.CharField(db_column='PaymentUUID',
                            max_length=36, default=uuid.uuid4, unique=True)

    expected_amount = models.DecimalField(db_column='ExpectedAmount', max_digits=18, decimal_places=2, blank=True,
                                          null=True)
    received_amount = models.DecimalField(db_column='ReceivedAmount', max_digits=18, decimal_places=2, blank=True,
                                          null=True)
    officer_code = models.CharField(
        db_column='OfficerCode', max_length=50, blank=True, null=True)
    phone_number = models.CharField(
        db_column='PhoneNumber', max_length=12, blank=True, null=True)
    request_date = fields.DateField(
        db_column='RequestDate', blank=True, null=True)
    received_date = fields.DateField(
        db_column='ReceivedDate', blank=True, null=True)
    status = models.IntegerField(
        db_column='PaymentStatus', blank=True, null=True)

    transaction_no = models.CharField(
        db_column='TransactionNo', max_length=50, blank=True, null=True)
    origin = models.CharField(
        db_column='PaymentOrigin', max_length=50, blank=True, null=True)
    matched_date = fields.DateField(
        db_column='MatchedDate', blank=True, null=True)
    receipt_no = models.CharField(
        db_column='ReceiptNo', max_length=100, blank=True, null=True)
    payment_date = fields.DateField(
        db_column='PaymentDate', blank=True, null=True)
    rejected_reason = models.CharField(
        db_column='RejectedReason', max_length=255, blank=True, null=True)
    date_last_sms = fields.DateField(
        db_column='DateLastSMS', blank=True, null=True)
    language_name = models.CharField(
        db_column='LanguageName', max_length=10, blank=True, null=True)
    type_of_payment = models.CharField(
        db_column='TypeOfPayment', max_length=50, blank=True, null=True)
    transfer_fee = models.DecimalField(
        db_column='TransferFee', max_digits=18, decimal_places=2, blank=True, null=True)
    reconc_req_id = models.CharField(
        db_column='SpReconcReqId', max_length=30, blank=True, null=True)
    reconciliation_date = models.DateTimeField(
        db_column='ReconciliationDate', null=True, blank=True)

    # rowid = models.TextField(db_column='RowID')
    # auditED, not audit ???
    # auditeduser_id = models.IntegerField(db_column='AuditedUSerID', blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'tblPayment'

    def __str__(self):
        return f"id:{self.id}, expected_amount: {self.expected_amount}, status:{self.status}, " \
               f"type:{self.type_of_payment}, uuid:{self.uuid}"


class PaymentDetail(core_models.VersionedModel):
    id = models.BigAutoField(db_column='PaymentDetailsID', primary_key=True)

    payment = models.ForeignKey(
        Payment, models.DO_NOTHING, db_column='PaymentID', related_name="payment_details")
    # beware putting FKs: product code (,...): need to check if we can/must adapt payment info if code (,...) change
    # i.e. normally, FK is pointing to PK, not to a field
    product_code = models.CharField(
        db_column='ProductCode', max_length=8, blank=True, null=True)
    insurance_number = models.CharField(
        db_column='InsuranceNumber', max_length=50, blank=True, null=True)  # CHF_ID

    policy_stage = models.CharField(
        db_column='PolicyStage', max_length=1, blank=True, null=True)
    amount = models.DecimalField(
        db_column='Amount', max_digits=18, decimal_places=2, blank=True, null=True)

    premium = models.ForeignKey(Premium,
                                models.SET_NULL, db_column='PremiumID', related_name="payment_details",
                                blank=True, null=True
                                )

    enrollment_date = fields.DateField(
        db_column='enrollmentDate', blank=True, null=True)
    expected_amount = models.DecimalField(db_column='ExpectedAmount', max_digits=18, decimal_places=2, blank=True,
                                          null=True)

    # rowid = models.TextField(db_column='RowID', blank=True, null=True)  # Field name made lowercase. This field type is a guess.
    # ! auditED in field name
    audit_user_id = models.IntegerField(
        db_column='AuditedUserId', blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'tblPaymentDetails'

    def __str__(self):
        return f"id:{self.id}, payment:{self.payment_id}, ins_nb:{self.insurance_number}, amount:{self.amount}, " \
               f"premium:{self.premium_id}"


class PaymentMutation(core_models.UUIDModel, core_models.ObjectMutation):
    payment = models.ForeignKey(
        Payment, models.DO_NOTHING, related_name='mutations')
    mutation = models.ForeignKey(
        core_models.MutationLog, models.DO_NOTHING, related_name='payments')

    class Meta:
        managed = True
        db_table = "payment_PaymentMutation"
