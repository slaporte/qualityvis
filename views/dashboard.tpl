<h1>loupes dashboard</h1>
<ul>
	<li>{{summary['in_progress_count']}} loupes in progress</li>
%if summary['in_progress']:
	<li>in progress:</li>
	<ul>
%for title, time in summary['in_progress'].iteritems():
		<li>{{title}} has taken {{time}}</li>
%end
    </ul>
%end
	<li>{{['in_progress']complete_count}} loupes complete</li>
	<li>{{['in_progress']success_count}} loupes all successful</li>
	<li>{{['in_progress']failure_count}} loupes had some failure</li>
</ul>