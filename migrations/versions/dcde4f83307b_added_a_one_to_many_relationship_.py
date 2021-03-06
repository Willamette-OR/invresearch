"""Added a one-to-many relationship between Stock and Post

Revision ID: dcde4f83307b
Revises: 6031e0bef3a6
Create Date: 2022-01-26 21:59:15.735425

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dcde4f83307b'
down_revision = '6031e0bef3a6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('post', sa.Column('stock_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'post', 'stock', ['stock_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'post', type_='foreignkey')
    op.drop_column('post', 'stock_id')
    # ### end Alembic commands ###
