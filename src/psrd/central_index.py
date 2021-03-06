import json
import sys
import os
import os.path
import psrd.sql
import psrd.sql.index
import psrd.sql.section_index
from psrd.sql.index.central_index import insert_central_index
from psrd.sql.index.url_ref import insert_url_reference
from psrd.sql.index.feat_type_index import insert_feat_type_index
from psrd.sql.index.spell_list_index import insert_spell_list_index
from psrd.sql.index.spell_subschool_index import insert_spell_subschool_index
from psrd.sql.index.spell_descriptor_index import insert_spell_descriptor_index
from psrd.sql.index.spell_component_index import insert_spell_component_index
from psrd.sql.index.search_alternatives import create_alternatives
from psrd.sql.index.books import insert_book
from psrd.sql.feats import fetch_feat_types
from psrd.sql.spells import fetch_spell_lists, fetch_spell_descriptors, fetch_spell_components, fetch_spell_subschools
from psrd.sql.url_ref import fetch_url_references

def build_central_index(db, conn, source_conn, db_name):
	curs = conn.cursor()
	source_curs = source_conn.cursor()
	try:
		psrd.sql.section_index.fetch_central_index(source_curs)
		index_source = source_curs.fetchall()
		book = False
		for item in index_source:
			if not book:
				insert_book(curs, item['source'], db_name)
				book = True
			item['database'] = db_name
			index_id = insert_central_index(curs, **item)
			create_alternatives(curs, index_id, item['search_name'])
			if item['type'] == 'feat':
				handle_feat(curs, source_curs, index_id, item['section_id'])
			elif item['type'] == 'spell':
				handle_spell(curs, source_curs, index_id, item['section_id'])
			handle_url_references(curs, source_curs, index_id, item['section_id'])
		conn.commit()
	finally:
		curs.close()
		source_curs.close()

def handle_feat(curs, source_curs, index_id, section_id):
	fetch_feat_types(source_curs, section_id)
	feat_types = source_curs.fetchall()
	for feat_type in feat_types:
		insert_feat_type_index(curs, index_id, feat_type['feat_type'])

def handle_spell(curs, source_curs, index_id, section_id):
	fetch_spell_lists(source_curs, section_id)
	for spell_list in source_curs.fetchall():
		insert_spell_list_index(curs, index_id,
			spell_list['level'], spell_list['class'], spell_list['magic_type'])
	fetch_spell_descriptors(source_curs, section_id)
	for spell_descriptor in source_curs.fetchall():
		insert_spell_descriptor_index(curs, index_id, spell_descriptor['descriptor'])
	fetch_spell_components(source_curs, section_id)
	for spell_component in source_curs.fetchall():
		insert_spell_component_index(curs, index_id, spell_component['component_type'])
	fetch_spell_subschools(source_curs, section_id)
	for spell_subschool in source_curs.fetchall():
		insert_spell_subschool_index(curs, index_id, spell_subschool['subschool'])

def handle_url_references(curs, source_curs, index_id, section_id):
	fetch_url_references(source_curs, section_id)
	refs = source_curs.fetchall()
	for ref in refs:
		insert_url_reference(curs, index_id, ref['url'])

def load_central_index(db, args, parent):
	conn = psrd.sql.index.get_db_connection(db)
	for arg in args:
		source_conn = psrd.sql.get_db_connection(arg)
		db_name = os.path.basename(arg)
		build_central_index(db, conn, source_conn, db_name)
