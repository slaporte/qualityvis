%try:
    %from bottle import request
    %if not request.query.get('ajax', False):
        %rebase layout
    %end
%except Exception:
    %rebase layout
%end

<h1>Loupe Dashboard</h1>
<p><input id="autorefresh" name="autorefresh" type="checkbox" /> <label for="autorefresh">Auto-update</label></p>
<div id="content">
<h2>Summary</h2>
<p class="infos">Run started on <span class="info">{{meta['host_machine']}}</span> at <span class="info">{{meta['start_time']}}</span> via <span class="info">{{meta['start_cmd']}}</span>.
%if summary['total_articles']:
    %completion = str(round(summary['complete_count'] / float(summary['total_articles']), 4) * 100) + '%'
    <p class="infos">Currently <span class="info">{{completion}}</span> complete.</p>
%end
<table id="sys-info">
    <thead>
        <th>Info</th>
        <th>Value</th>
        <th>Peak</th>
    </thead>
    <tbody>
        <tr>
            <td class='label'>CPU</td>
            <td class='text'>{{round(sys['cpu_pct'], 2)}}%</td>
            <td class='text'>{{round(sys_peaks['cpu_pct'], 2)}}%</td>
        </tr>
        <tr>
            <td class='label'>Memory</td>
            <td class='text'>{{round(sys['mem_info'] / (1024 * 1024), 3)}} MB / {{round(sys['mem_pct'], 2)}}%</td>
            <td class='text'>{{round(sys_peaks['mem_info'] / (1024 * 1024), 3)}} MB / {{round(sys_peaks['mem_pct'], 2)}}%</td>
        </tr>
        <tr>
            <td class='label'>Connections</td>
            <td class='text'>{{sys['no_connections']}}</td>
            <td class='text'>{{sys_peaks['no_connections']}}</td>
        </tr>
    </tbody>
</table>

<br/>

<table id="conn-info">
    <thead>
        <th>Connection state</th>
        <th>Number</th>
    </thead>
    <tbody>
        <tr>
            <td class='label'>Connecting</td><td>{{sys['connections']['SYN_SENT']}}</td>
        </tr>
        <tr>
            <td class='label'>Established</td><td>{{sys['connections']['ESTABLISHED']}}</td>
        </tr>
        <tr>
            <td class='label'>Listening</td><td>{{sys['connections']['LISTEN']}}</td>
        </tr>
        <tr>
            <td class='label'>Closing</td><td>{{sys['connections']['CLOSE_WAIT']}}</td>
        </tr>
        <tr>
            <td class='label'>Closed</td><td>{{sys['connections']['CLOSE']}}</td>
        </tr>
    </tbody>
</table>

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
                %elif in_attempts > 0:
                <td class="input-retried">
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
%total = float(summary['complete_count'])
%formatted_dur = "{:.2f}".format(meta['duration'])
%if total > 0:
    %sec_per_loupe = round(meta['duration']/total, 3)
%else:
    %sec_per_loupe = '?'
%end
<p class="infos">We have completed <span class="info">{{total}} loupes</span> in <span class="info">{{formatted_dur}}s</span> (<span class="info">{{sec_per_loupe}}</span> sec/loupe).</p>
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
            %total_times = [time['durations'].get(i_name, {}).get('total') for time in complete if time.get('durations', {}).get(i_name, {}).get('total')]
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
                %av_proc = round(sum(proc_times) / len(proc_times), 3)
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
%if total:
<h2>Stat failures</h2>
%total_errs = len(failed_stats)
<p class="infos">We have <span class="info">{{total_errs}}</span> types of stat failures.</p>
<table id="failure-table">
    <thead>
        <th>Input</th>
        <th>Stat</th>
        <th>Error</th>
        <th>Total</th>
        <th>Fail rate</th>
        <th>Example</th>
    </thead>
    <tbody>
        %for (failed_stat, f_titles) in failed_stats.iteritems():
        <tr>
            <td class='label'>{{failed_stat[0]}}</td>
            <td class='label'>{{failed_stat[1]}}</td>
            <td class='text'>{{failed_stat[2]}}</td>
            <td>{{len(f_titles)}}</td>
            <td>{{round(len(f_titles) / float(total), 2) * 100}}%</td>
            <td><a href='https://en.wikipedia.org/wiki/{{f_titles[0].replace(' ', '_')}}'>{{f_titles[0]}}</a></td>
        </tr>
        %end
    </tbody>
</table>
%end
<h2>Fetch failures</h2>
%fetch_errs = len(fetch_failures)
<p class="infos">We have <span class="info">{{fetch_errs}}</span> articles with fetch failures.</p>
<table id="fetch-failure-table">
    <thead>
        <th>Article</th>
        <th>No. input fetch failures</th>
        <th>Fetch failures</th>
    </thead>
    <tbody>
        %for (failed_input, f_total) in fetch_failures.iteritems():
        <tr>
            <td class='label'>{{failed_input}}</td>
            <td>{{len(f_total)}}</td>
            <td>{{', '.join(f_total)}}
        </tr>
        %end
    </tbody>
</table>
