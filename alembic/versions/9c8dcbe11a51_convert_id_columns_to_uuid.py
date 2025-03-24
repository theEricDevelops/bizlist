"""Convert ID Columns to UUID

Revision ID: 9c8dcbe11a51
Revises: e90f15aaa9c6
Create Date: 2025-03-24 12:32:48.700152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '9c8dcbe11a51'
down_revision: Union[str, None] = 'e90f15aaa9c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Install pgcrypto extension for gen_random_uuid()
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')
    
    # Add UUID columns to the tables
    op.add_column('businesses', sa.Column('uuid_id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()')))
    op.add_column('contacts', sa.Column('uuid_id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()')))
    op.add_column('sources', sa.Column('uuid_id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()')))
    op.add_column('coverage_zip_list', sa.Column('uuid_id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()')))
    
    # Create new join tables with UUID columns
    op.execute('''
    CREATE TABLE business_contacts_new (
        business_uuid UUID NOT NULL,
        contact_uuid UUID NOT NULL,
        PRIMARY KEY (business_uuid, contact_uuid)
    )
    ''')
    
    op.execute('''
    CREATE TABLE business_sources_new (
        business_uuid UUID NOT NULL,
        source_uuid UUID NOT NULL,
        PRIMARY KEY (business_uuid, source_uuid)
    )
    ''')
    
    op.execute('''
    CREATE TABLE source_contacts_new (
        source_uuid UUID NOT NULL,
        contact_uuid UUID NOT NULL,
        PRIMARY KEY (source_uuid, contact_uuid)
    )
    ''')
    
    # Copy and map data from integer IDs to UUIDs for join tables
    op.execute('''
    INSERT INTO business_contacts_new (business_uuid, contact_uuid)
    SELECT b.uuid_id, c.uuid_id
    FROM business_contacts bc
    JOIN businesses b ON b.id = bc.business_id
    JOIN contacts c ON c.id = bc.contact_id
    ''')
    
    op.execute('''
    INSERT INTO business_sources_new (business_uuid, source_uuid)
    SELECT b.uuid_id, s.uuid_id
    FROM business_sources bs
    JOIN businesses b ON b.id = bs.business_id
    JOIN sources s ON s.id = bs.source_id
    ''')
    
    op.execute('''
    INSERT INTO source_contacts_new (source_uuid, contact_uuid)
    SELECT s.uuid_id, c.uuid_id
    FROM source_contacts sc
    JOIN sources s ON s.id = sc.source_id
    JOIN contacts c ON c.id = sc.contact_id
    ''')
    
    # Drop old join tables and rename new ones
    op.drop_table('business_contacts')
    op.drop_table('business_sources')
    op.drop_table('source_contacts')
    
    op.rename_table('business_contacts_new', 'business_contacts')
    op.rename_table('business_sources_new', 'business_sources')
    op.rename_table('source_contacts_new', 'source_contacts')
    
    # Lookup the actual PK constraint names before dropping
    conn = op.get_bind()
    
    # For businesses table - using text() function
    pk_query = text("""
    SELECT constraint_name FROM information_schema.table_constraints
    WHERE table_name = 'businesses' AND constraint_type = 'PRIMARY KEY'
    """)
    businesses_pk = conn.execute(pk_query).scalar()
    if businesses_pk:
        op.execute(f'ALTER TABLE businesses DROP CONSTRAINT "{businesses_pk}"')
    op.drop_column('businesses', 'id')
    op.alter_column('businesses', 'uuid_id', new_column_name='id')
    op.create_primary_key('businesses_pkey', 'businesses', ['id'])
    
    # For contacts table - using text() function
    pk_query = text("""
    SELECT constraint_name FROM information_schema.table_constraints
    WHERE table_name = 'contacts' AND constraint_type = 'PRIMARY KEY'
    """)
    contacts_pk = conn.execute(pk_query).scalar()
    if contacts_pk:
        op.execute(f'ALTER TABLE contacts DROP CONSTRAINT "{contacts_pk}"')
    op.drop_column('contacts', 'id')
    op.alter_column('contacts', 'uuid_id', new_column_name='id')
    op.create_primary_key('contacts_pkey', 'contacts', ['id'])
    
    # For sources table - using text() function
    pk_query = text("""
    SELECT constraint_name FROM information_schema.table_constraints
    WHERE table_name = 'sources' AND constraint_type = 'PRIMARY KEY'
    """)
    sources_pk = conn.execute(pk_query).scalar()
    if sources_pk:
        op.execute(f'ALTER TABLE sources DROP CONSTRAINT "{sources_pk}"')
    op.drop_column('sources', 'id')
    op.alter_column('sources', 'uuid_id', new_column_name='id')
    op.create_primary_key('sources_pkey', 'sources', ['id'])
    
    # For coverage_zip_list table - using text() function
    pk_query = text("""
    SELECT constraint_name FROM information_schema.table_constraints
    WHERE table_name = 'coverage_zip_list' AND constraint_type = 'PRIMARY KEY'
    """)
    coverage_pk = conn.execute(pk_query).scalar()
    if coverage_pk:
        op.execute(f'ALTER TABLE coverage_zip_list DROP CONSTRAINT "{coverage_pk}"')
    op.drop_column('coverage_zip_list', 'id')
    op.alter_column('coverage_zip_list', 'uuid_id', new_column_name='id')
    op.create_primary_key('coverage_zip_list_pkey', 'coverage_zip_list', ['id'])
    
    # Rename join table columns for consistency
    op.alter_column('business_contacts', 'business_uuid', new_column_name='business_id')
    op.alter_column('business_contacts', 'contact_uuid', new_column_name='contact_id')
    op.alter_column('business_sources', 'business_uuid', new_column_name='business_id')
    op.alter_column('business_sources', 'source_uuid', new_column_name='source_id')
    op.alter_column('source_contacts', 'source_uuid', new_column_name='source_id')
    op.alter_column('source_contacts', 'contact_uuid', new_column_name='contact_id')
    
    # Add foreign key constraints back to join tables
    op.create_foreign_key(
        'business_contacts_business_id_fkey', 'business_contacts', 'businesses',
        ['business_id'], ['id']
    )
    op.create_foreign_key(
        'business_contacts_contact_id_fkey', 'business_contacts', 'contacts',
        ['contact_id'], ['id']
    )
    
    op.create_foreign_key(
        'business_sources_business_id_fkey', 'business_sources', 'businesses',
        ['business_id'], ['id']
    )
    op.create_foreign_key(
        'business_sources_source_id_fkey', 'business_sources', 'sources',
        ['source_id'], ['id']
    )
    
    op.create_foreign_key(
        'source_contacts_source_id_fkey', 'source_contacts', 'sources',
        ['source_id'], ['id']
    )
    op.create_foreign_key(
        'source_contacts_contact_id_fkey', 'source_contacts', 'contacts',
        ['contact_id'], ['id']
    )


def downgrade() -> None:
    """
    Revert UUID IDs back to integer IDs.
    Note: This is a destructive operation that generates new IDs.
    """
    # This is complex and potentially data-losing, so we'll implement a basic version
    
    # Create new tables with integer IDs
    op.execute('''
    CREATE TABLE businesses_int (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) UNIQUE NOT NULL,
        industry VARCHAR(255),
        address VARCHAR(255),
        address2 VARCHAR(255),
        city VARCHAR(255),
        state VARCHAR(255),
        zip VARCHAR(20),
        phone VARCHAR(20),
        website VARCHAR(255),
        email VARCHAR(255),
        notes TEXT
    )
    ''')
    
    op.execute('''
    CREATE TABLE contacts_int (
        id SERIAL PRIMARY KEY,
        first_name VARCHAR(255) NOT NULL,
        last_name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE,
        phone VARCHAR(20),
        title VARCHAR(255),
        notes TEXT
    )
    ''')
    
    op.execute('''
    CREATE TABLE sources_int (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) UNIQUE NOT NULL,
        url VARCHAR(255) UNIQUE,
        notes TEXT
    )
    ''')
    
    op.execute('''
    CREATE TABLE coverage_zip_list_int (
        id SERIAL PRIMARY KEY,
        params TEXT UNIQUE NOT NULL,
        zips TEXT NOT NULL
    )
    ''')
    
    # Copy data to new tables
    op.execute('''
    INSERT INTO businesses_int (name, industry, address, address2, city, state, zip, phone, website, email, notes)
    SELECT name, industry, address, address2, city, state, zip, phone, website, email, notes
    FROM businesses
    ''')
    
    op.execute('''
    INSERT INTO contacts_int (first_name, last_name, email, phone, title, notes)
    SELECT first_name, last_name, email, phone, title, notes
    FROM contacts
    ''')
    
    op.execute('''
    INSERT INTO sources_int (name, url, notes)
    SELECT name, url, notes
    FROM sources
    ''')
    
    op.execute('''
    INSERT INTO coverage_zip_list_int (params, zips)
    SELECT params, zips
    FROM coverage_zip_list
    ''')
    
    # Create mapping for old UUIDs to new integer IDs
    op.execute('CREATE TABLE uuid_to_int_business AS SELECT id AS uuid, id AS int FROM businesses_int')
    op.execute('CREATE TABLE uuid_to_int_contact AS SELECT id AS uuid, id AS int FROM contacts_int')
    op.execute('CREATE TABLE uuid_to_int_source AS SELECT id AS uuid, id AS int FROM sources_int')
    
    # Create new join tables
    op.execute('''
    CREATE TABLE business_contacts_int (
        business_id INTEGER REFERENCES businesses_int(id),
        contact_id INTEGER REFERENCES contacts_int(id),
        PRIMARY KEY (business_id, contact_id)
    )
    ''')
    
    op.execute('''
    CREATE TABLE business_sources_int (
        business_id INTEGER REFERENCES businesses_int(id),
        source_id INTEGER REFERENCES sources_int(id),
        PRIMARY KEY (business_id, source_id)
    )
    ''')
    
    op.execute('''
    CREATE TABLE source_contacts_int (
        source_id INTEGER REFERENCES sources_int(id),
        contact_id INTEGER REFERENCES contacts_int(id),
        PRIMARY KEY (source_id, contact_id)
    )
    ''')
    
    # Drop all the original tables with UUID keys
    op.drop_table('business_contacts')
    op.drop_table('business_sources')
    op.drop_table('source_contacts')
    op.drop_table('businesses')
    op.drop_table('contacts')
    op.drop_table('sources')
    op.drop_table('coverage_zip_list')
    
    # Rename the new tables to the original names
    op.rename_table('businesses_int', 'businesses')
    op.rename_table('contacts_int', 'contacts')
    op.rename_table('sources_int', 'sources')
    op.rename_table('coverage_zip_list_int', 'coverage_zip_list')
    op.rename_table('business_contacts_int', 'business_contacts')
    op.rename_table('business_sources_int', 'business_sources')
    op.rename_table('source_contacts_int', 'source_contacts')
    
    # Drop the mapping tables
    op.drop_table('uuid_to_int_business')
    op.drop_table('uuid_to_int_contact')
    op.drop_table('uuid_to_int_source')
