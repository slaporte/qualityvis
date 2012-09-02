%rebase layout

<h1>Loupe</h1>
%if in_progress:
<h2>Articles in Progress</h2>
<table id="in-prog-table">
    <thead>
        <th>#</th>
        <th>Article</th>
        <th>Tot time</th>
        %for i_name in input_classes:
        <th>{{i_name}}</th>
        %end
    </thead>
    <tbody>
    %for status in sorted(in_progress, key=lambda s: s.get('create_i', s['title'])):
        <tr>
            <td>{{status.get('create_i')}}</td>
            <td>{{status['title']}}</td>
            <td>{{round(status['durations']['total'], 1)}}</td>
            %for i_name in input_classes:
            %in_duration = status['durations'].get(i_name, {}).get('total', 0.0)
            %in_status = status['inputs'][i_name]
            %in_attempts = in_status['attempts']
            %in_success = in_status['is_successful']
            %in_complete = in_status['is_complete']
                %if in_success:
                <td class="input-success">
                %elif in_complete:
                <td class="input-failure">
                %else:
                <td class="input-incomplete">
                %end
            {{round(in_duration, 1)}} ({{in_attempts}})</td>
            %end
        </tr>
    %end
    </tbody>
</table>
%end
