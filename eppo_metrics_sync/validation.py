from collections import Counter

advanced_aggregation_parameters = [
    'retention_threshold_days',
    'conversion_threshold_days',
    'threshold_metric_settings'
]

winsorization_parameters = [
    'winsorization_lower_percentile',
    'winsorization_upper_percentile'
]

timeframe_parameters = [
    'aggregation_timeframe_start_value',
    'aggregation_timeframe_end_value',
    'aggregation_timeframe_unit'
]


def check_for_duplicated_names(payload, names, object_name):
    element_counts = Counter(names)
    duplicate_elements = [i for i, count in element_counts.items() if count > 1]
    if duplicate_elements:
        payload.validation_errors.append(
            object_name + ' names are not unique: ' + ', '.join(duplicate_elements)
        )


def unique_names(payload):
    fact_source_names = []
    fact_names = []
    fact_property_names = []

    for fact_source in payload.fact_sources:
        fact_source_names.append(fact_source['name'])
        fact_names.extend([f['name'] for f in fact_source['facts']])
        if ('properties' in fact_source):
            fact_property_names.extend(
                [f['name'] for f in fact_source['properties']]
            )

    metric_names = [m['name'] for m in payload.metrics]

    check_for_duplicated_names(payload, fact_source_names, 'Fact source')
    check_for_duplicated_names(payload, fact_names, 'Fact')
    # TODO: check for distinct names within a given fact source
    # check_for_duplicated_names(payload, fact_property_names, 'Fact property')
    check_for_duplicated_names(payload, metric_names, 'Metric')

    return True


def valid_fact_references(payload):
    fact_references = set()
    for metric in payload.metrics:
        if 'numerator' in metric:
            fact_references.add(metric['numerator']['fact_name'])
        if 'denominator' in metric:
            fact_references.add(metric['denominator']['fact_name'])
        if 'percentile' in metric:
            fact_references.add(metric['percentile']['fact_name'])

    fact_names = set()
    for fact_source in payload.fact_sources:
        for fact in fact_source['facts']:
            fact_names.add(fact['name'])

    if fact_references.issubset(set(fact_names)) == False:
        payload.validation_errors.append(
            "Invalid fact reference(s): " +
            str(', '.join(fact_references.difference(fact_names)))
        )

def valid_experiment_computation(payload):
    for fact_source in payload.fact_sources:
        if 'properties' in fact_source:
            for property in fact_source['properties']:
                if 'include_experiment_computation' in property:
                    if not isinstance(property['include_experiment_computation'], bool):
                        payload.validation_errors.append(
                            f"Invalid include_experiment_computation value. It must be a boolean value for property: {property['name']}"
                        )

def metric_aggregation_is_valid(payload):
    for m in payload.metrics:
        if m.get('type') == 'percentile':
            percentile_error = percentile_metric_is_valid(m)
            if percentile_error:
                payload.validation_errors.append(
                    f"{m['name']} has invalid percentile configuration: {percentile_error}"
                )
            # Skip the rest of the loop iteration for percentile metrics
            # since they don't have numerator/denominator to validate
            continue

        if 'numerator' in m:
            numerator_error = aggregation_is_valid(m['numerator'])
            if numerator_error:
                payload.validation_errors.append(
                    f"{m['name']} has invalid numerator: {numerator_error}"
                )

        if 'denominator' in m:
            denominator_error = aggregation_is_valid(m['denominator'])
            if denominator_error:
                payload.validation_errors.append(
                    f"{m['name']} has invalid denominator: {denominator_error}"
                )


def valid_guardrail_cutoff_signs(payload):
    facts = dict()
    for fact_source in payload.fact_sources:
        for fact in fact_source['facts']:
            facts[fact['name']] = fact

    for m in payload.metrics:
        if m.get('type') == 'percentile':
            if is_guardrail_cutoff_exist(m):
                percentile_fact_name = m['percentile']['fact_name']
                if percentile_fact_name in facts and 'desired_change' in facts[percentile_fact_name]:
                    error = is_valid_guardrail_cutoff_sign(m, facts[percentile_fact_name])
                    if error:
                        payload.validation_errors.append(
                            f"{m['name']} is having invalid guardrail_cutoff sign: {error}"
                        )
            # Skip the rest of the loop iteration for percentile metrics
            # since they don't have numerator/denominator to validate
            continue

        if 'numerator' in m:
            numerator_fact_name = m['numerator']['fact_name']
            if is_guardrail_cutoff_exist(m) and numerator_fact_name in facts and 'desired_change' in facts[numerator_fact_name]:
                error = is_valid_guardrail_cutoff_sign(m, facts[numerator_fact_name])
                if error:
                    payload.validation_errors.append(
                        f"{m['name']} is having invalid guardrail_cutoff sign: {error}"
                    )


def is_valid_guardrail_cutoff_sign(metric, numerator_fact):
    if numerator_fact['desired_change'] == 'decrease' and metric['guardrail_cutoff'] < 0:
        return f"guardrail_cutoff value should be positive"
    elif numerator_fact['desired_change'] == 'increase' and metric['guardrail_cutoff'] > 0:
        return f"guardrail_cutoff value should be negative"


def is_guardrail_cutoff_exist(metric):
    return 'is_guardrail' in metric and metric['is_guardrail'] and 'guardrail_cutoff' in metric


def distinct_advanced_aggregation_parameter_set(
        aggregation,
        operation,
        aggregation_parameter,
        error_message
):
    if aggregation['operation'] == operation:
        matched = [p for p in advanced_aggregation_parameters if p in aggregation]
        if len(matched) == 0:
            error_message.append(
                f'{operation} aggregation must have {aggregation_parameter} set'
            )
        elif len(matched) == 1 and matched[0] == aggregation_parameter:
            return True
        else:
            invalid_elements = [m for m in matched if m != aggregation_parameter]
            error_message.append(
                f"Invalid parameter for {operation} aggregation: {', '.join(invalid_elements)}"
            )


def aggregation_is_valid(aggregation):
    error_message = []

    if aggregation['operation'] not in ['sum', 'count', 'count_distinct', 'distinct_entity', 'threshold', 'retention',
                                        'conversion', 'last_value', 'first_value']:
        error_message.append(
            'Invalid aggregation operation: ' + aggregation['operation']
        )

    # can only winsorize operations in the list immediately following this line
    if aggregation['operation'] not in ['sum', 'count', 'count_distinct', 'last_value', 'first_value']:
        if [name for name in winsorization_parameters if name in aggregation]:
            error_message.append(
                'Cannot winsorize a metric with operation ' + aggregation['operation']
            )

    # The aggregation_timeframe_unit must be specified if timeframe parameters are set
    included_timeframe_parameters = [name for name in timeframe_parameters if name in aggregation]

    if 'aggregation_timeframe_value' in aggregation:
        error_message.append(
            'The aggregation_timeframe_value parameter has been deprecated. Please use aggregation_timeframe_end instead.'
        )

    timeframe_unit_specified = 'aggregation_timeframe_unit' in included_timeframe_parameters
    if len(included_timeframe_parameters) > 0 and not timeframe_unit_specified:
        error_message.append(
            'The aggregation_timeframe_unit must be set to use timeframe parameters.'
        )

    # only set timeframe_parameters on some operation types
    if aggregation['operation'] in ['conversion']:
        matched = [p for p in timeframe_parameters if p in aggregation]
        if matched:
            error_message.append(
                "Cannot specify " + matched[0] + " for operation " + aggregation['operation']
            )

    # can't specify advanced aggregation parameters for simple aggregation types
    if aggregation['operation'] not in ['threshold', 'retention', 'conversion']:
        matched = [p for p in advanced_aggregation_parameters if p in aggregation]
        if matched:
            error_message.append(
                matched[0] + ' specified, but operation is ' + aggregation['operation']
            )

    # if threshold:
    if aggregation['operation'] == 'threshold':
        # TODO
        pass

    distinct_advanced_aggregation_parameter_set(
        aggregation,
        'retention',
        'retention_threshold_days',
        error_message
    )
    distinct_advanced_aggregation_parameter_set(
        aggregation,
        'conversion',
        'conversion_threshold_days',
        error_message
    )
    distinct_advanced_aggregation_parameter_set(
        aggregation,
        'threshold',
        'threshold_metric_settings',
        error_message
    )

    if error_message:
        return '\n'.join(error_message)
    else:
        return None

def percentile_metric_is_valid(metric):
    error_message = []

    # Check for required percentile field
    if 'percentile' not in metric:
        error_message.append("Missing 'percentile' field for percentile metric")
        return '\n'.join(error_message)

    percentile = metric['percentile']

    # Check for required fact_name
    if 'fact_name' not in percentile:
        error_message.append("Missing 'fact_name' in percentile configuration")

    # Check for required percentile_value
    if 'percentile_value' not in percentile:
        error_message.append("Missing 'percentile_value' in percentile configuration")
    elif not isinstance(percentile['percentile_value'], (int, float)):
        error_message.append("'percentile_value' must be a number")
    elif percentile['percentile_value'] < 0 or percentile['percentile_value'] > 1:
        error_message.append("'percentile_value' must be between 0 and 1")

    if error_message:
        return '\n'.join(error_message)
    else:
        return None
