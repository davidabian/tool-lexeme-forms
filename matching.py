import copy


# whether the presence of some statement for a property
# rules the lexeme out as a match for a template
# with a different statement for that property
properties_exclusive = {
    'www': {
        # other “instance of” are likely unrelated and okay
        'P31': False,
        # other “grammatical gender” are incompatible
        'P5185': True,
        # other “grammatical aspect” are incompatible
        'P7486': True,
    },
    'test': {
        # other “instance of” are likely unrelated and okay
        'P82': False,
        # other “grammatical gender” are incompatible
        'P73601': True,
    },
}


def match_template_to_lexeme_data(template, lexeme_data):
    language_matches = template['language_item_id'] == lexeme_data['language']
    lexical_category_matches = template['lexical_category_item_id'] == lexeme_data['lexicalCategory']
    matched_statements, missing_statements, conflicting_statements = match_template_entity_to_lexeme_entity('test' in template, template, lexeme_data)

    return {
        'language': language_matches,
        'lexical_category': lexical_category_matches,
        'matched_statements': matched_statements,
        'missing_statements': missing_statements,
        'conflicting_statements': conflicting_statements,
    }


def match_template_entity_to_lexeme_entity(test, template_entity, lexeme_entity): # may be template + lexeme or template form + lexeme form
    matched_statements = {}
    missing_statements = {}
    conflicting_statements = {}

    properties_exclusive_for_template_entity = properties_exclusive['test' if test else 'www']
    for property_id in template_entity.get('statements', {}):
        property_exclusive = properties_exclusive_for_template_entity[property_id]
        for template_statement in template_entity['statements'][property_id]:
            found_matching_statement = False
            if lexeme_entity.get('claims') == []:
                lexeme_entity['claims'] = {} # work around T241422
            for lexeme_statement in lexeme_entity.get('claims', {}).get(property_id, []):
                if match_statement(template_statement, lexeme_statement):
                    found_matching_statement = True
                    if property_id not in matched_statements:
                        matched_statements[property_id] = []
                    matched_statements[property_id].append(lexeme_statement)
                elif property_exclusive:
                    if property_id not in conflicting_statements:
                        conflicting_statements[property_id] = []
                    conflicting_statements[property_id].append(lexeme_statement)

            if not found_matching_statement:
                if property_id not in missing_statements:
                    missing_statements[property_id] = []
                missing_statements[property_id].append(template_statement)

    return matched_statements, missing_statements, conflicting_statements


def match_statement(template_statement, lexeme_statement):
    # so far, we only compare the main snak (ignoring qualifiers and references),
    # and only support entity ID values, because that’s all the templates use
    if lexeme_statement['mainsnak']['snaktype'] == 'value':
        template_statement_value_id = template_statement['mainsnak']['datavalue']['value']['id']
        lexeme_statement_value_id = lexeme_statement['mainsnak']['datavalue']['value']['id']
        return template_statement_value_id == lexeme_statement_value_id
    else:
        return False


def match_lexeme_forms_to_template(lexeme_forms, template):
    template = copy.deepcopy(template)
    for lexeme_form in lexeme_forms:
        best_template_forms = match_lexeme_form_to_template_forms('test' in template, lexeme_form, template['forms'])
        if len(best_template_forms) == 1:
            best_template_form = best_template_forms[0]
            best_template_form.setdefault('lexeme_forms', []).append(lexeme_form)
        elif best_template_forms:
            template.setdefault('ambiguous_lexeme_forms', []).append(lexeme_form)
        else:
            template.setdefault('unmatched_lexeme_forms', []).append(lexeme_form)
    return template


def match_lexeme_form_to_template_forms(test, lexeme_form, template_forms):
    best_template_forms = []
    best_matching_features = 0
    for template_form in template_forms:
        matching_features = match_lexeme_form_to_template_form(test, lexeme_form, template_form)
        if matching_features > best_matching_features:
            best_matching_features = matching_features
            best_template_forms = [template_form]
        elif matching_features == best_matching_features and best_matching_features > 0:
            best_template_forms.append(template_form)
    if not best_template_forms and len(template_forms) == 1 and matchable_features(template_form) == 0:
        # as a special exception, in a template with a single featureless form, a lexeme form is allowed to match with no matching features
        return [template_forms[0]]
    return best_template_forms


def match_lexeme_form_to_template_form(test, lexeme_form, template_form):
    matching_features = 0

    for grammatical_feature_item_id in template_form['grammatical_features_item_ids']:
        if grammatical_feature_item_id in lexeme_form['grammaticalFeatures']:
            matching_features += 1
        else:
            return 0

    matched_statements, missing_statements, conflicting_statements = match_template_entity_to_lexeme_entity(test, template_form, lexeme_form)
    if missing_statements or conflicting_statements:
        return 0
    else:
        matching_features += len(matched_statements)

    return matching_features


def matchable_features(template_form):
    features = len(template_form['grammatical_features_item_ids'])
    for property_id in template_form.get('statements', {}):
        features += len(template_form['statements'][property_id])
    return features
