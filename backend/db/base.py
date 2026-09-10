# Import all the models, so that Base has them before being
# imported by Alembic
from db.base_class import Base

from models.user import User
from models.statement import StatementUpload
from models.transaction import Transaction, IncomeRecord, ExpenseRecord
from models.custom_rule import CustomRule
from models.receipt import Receipt
from models.category import Category
from models.asset import Asset
from models.tax import TaxComputation, TaxReport
from models.advisory import AIAdvisoryQuery
from models.knowledge_chunk import KnowledgeChunk
