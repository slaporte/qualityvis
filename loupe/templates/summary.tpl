<h1>loupes summary</h1>
<ul>
	<li>{{in_progress_count}} loupes in progress</li>
%if in_progress:
	<li>in progress:</li>
	<ul>
%for title, time in in_progress.iteritems():
		<li>{{title}} has taken {{time}}</li>
%end
    </ul>
%end
	<li>{{complete_count}} loupes complete</li>
	<li>{{success_count}} loupes all successful</li>
	<li>{{failure_count}} loupes had some failure</li>
</ul>