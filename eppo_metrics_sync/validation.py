from collections import Counter

simple_aggregation_options = ['sum', 'count', 'distinct_entity']

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
    'aggregation_timeframe_value',
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
        if('properties' in fact_source):
            fact_property_names.extend(
                [f['name'] for f in fact_source['properties']]
            )

    metric_names = [m['name'] for m in payload.metrics]

    check_for_duplicated_names(payload, fact_source_names, 'Fact source')
    check_for_duplicated_names(payload, fact_names, 'Fact')
    # TODO: check for distinct names within a given fact source
    #check_for_duplicated_names(payload, fact_property_names, 'Fact property')
    check_for_duplicated_names(payload, metric_names, 'Metric')
    
    return True


def valid_fact_references(payload):

    fact_references = set()
    for metric in payload.metrics:
        fact_references.add(metric['numerator']['fact_name'])
        if 'denominator' in metric:
            fact_references.add(metric['denominator']['fact_name'])

    fact_names = set()
    for fact_source in payload.fact_sources:
        for fact in fact_source['facts']:
            fact_names.add(fact['name'])

    if fact_references.issubset(set(fact_names)) == False:
        payload.validation_errors.append(
            "Invalid fact reference(s): " + 
            str(', '.join(fact_references.difference(fact_names)))
        )


def metric_aggregation_is_valid(payload):
    for m in payload.metrics:

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

    # can only winsorize sum or count metrics
    if aggregation['operation'] not in ['sum', 'count']:
        if [name for name in winsorization_parameters if name in aggregation]:
            error_message.append(
                'Cannot winsorize a metric with operation ' + aggregation['operation']
            )
        
    # either 0 or 2 of timeframe_parameters must be set
    if len([name for name in timeframe_parameters if name in aggregation]) == 1:
        error_message.append(
            'Either both or neither aggregation_timeframe_value and ' +
            'aggregation_timeframe_unit must be set'
        )

    # only set timeframe_parameters on a some operation types
    if aggregation['operation'] not in simple_aggregation_options:
        matched = [p for p in timeframe_parameters if p in aggregation]
        if matched:
            error_message.append(
                "Cannot specify " + matched[0] + " for operation " + aggregation['operation']
            )

    # can't specify advanced aggregation parameters for simple aggregation types
    if aggregation['operation'] in simple_aggregation_options:
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
    