%from bottle import request
%if not request.query.get('ajax', False):
%rebase layout
%end

<h1>Loupe Dashboad</h1>
<p><input id="autorefresh" name="autorefresh" type="checkbox" /> <label for="autorefresh">Auto-update</label></p>
<h2>Summary</h2>
<p class="infos">Run started on <span class="info">{{meta['host_machine']}}</span> at <span class="info">{{meta['start_time']}}</span> via <span class="info">{{meta['start_cmd']}}</span>.
<div id="content">
%if summary['total_articles']:
    %completion = str(round(summary['complete_count'] / float(summary['total_articles']), 4) * 100) + '%'
    <p class="infos">Currently <span class="info">{{completion}}</span> complete.</p>
%end
%if in_progress:
<h2>Articles in Progress</h2>
<p class="infos">There are <span class="info">{{summary['in_progress_count']}} loupes</span> in progress.</p>
<table id="in-prog-table">
    <thead>
        <th>#</th>
        <th>Article</th>
        <th>Total</th>
        %for i_name in input_classes:
        <th>{{i_name}}</th>
        %end
    </thead>
    <tbody>
    %for status in sorted(in_progress, key=lambda s: s.get('create_i', s['title'])):
        <tr>
            <td>{{status.get('create_i')}}</td>
            <td class='label'>{{status['title']}}</td>
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
<h2>Completion</h2>
%total = summary['complete_count']
<p class="infos">We have completed <span class="info">{{total}} loupes</span>.</p>
<table id="inputs-table">
    <thead>
        <th>Input name</th>
        <th>Average time (max)</th>
        <th>Average fetch time</th>
        <th>Average process time</th>
        <th>Success rate</th>
    </thead>
    <tbody>
        %for i_name in input_classes:
        <tr>
            <td class='label'>{{i_name}}</td>
            %total_times = [time['durations'].get(i_name, {}).get('total') for time in complete if time['durations'].get(i_name, {}).get('total')]
            %if len(total_times):
                %av_total = round(sum(total_times) / len(total_times), 1)
                %max_total = round(max(total_times), 1)
            %else:
                %av_total = '?'
                %max_total = '?'
            %end
            %fetch_times = [time['durations'].get(i_name, {}).get('fetch') for time in complete if time['durations'].get(i_name, {}).get('fetch')]
            %if len(fetch_times):
                %av_fetch = round(sum(fetch_times) / len(fetch_times), 1)
            %else:
                %av_fetch = '?'
            %end
            %proc_times = [time['durations'].get(i_name, {}).get('process') for time in complete if time['durations'].get(i_name, {}).get('process')]
            %if len(proc_times):
                %av_proc = round(sum(proc_times) / len(proc_times), 5)
            %else:
                %av_proc = '?'
            %end
            %success = len([input['title'] for input in complete if input['inputs'].get(i_name, {}).get('is_successful')])
            %if total:
                %success_percent = (success / total) * 100
                %success = str(round(success_percent, 0)) + '%'
            %end
            <td>{{av_total}} ({{max_total}})</td>
            <td>{{av_fetch}}</td>
            <td>{{av_proc}}</td>
            <td>{{success}}</td>
        </tr>
        %end
    </tbody>
</table>