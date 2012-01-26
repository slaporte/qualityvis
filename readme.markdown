# Article Quality Visualization
This is a javascript gadget for visualizing article quality in the English Wikipdia. We built this gadget for the [San Francisco Mediawiki Hackathon in 2012](https://www.mediawiki.org/wiki/January_2012_San_Francisco_Hackathon "SF Mediawiki Hackathon").

![Demo screenshot](/slaporte/qualityvis/raw/master/screen.png)

## Instillation and use
To use on the English Wikipedia, copy the contents of gadget.js into your common.js, and copy the contents of style.css into your common.css. For more detailed instructions on installing userscripts, [see here](http://en.wikipedia.org/wiki/Wikipedia:WikiProject_User_scripts/Scripts#Installing "more info").

## Methodology
We used a number of metrics aggregated into four areas of quality: richness, structure, integratedness, community, citations, and significance. Each metric can be individually weighted, although they have not all been incorporated into the ranking formula.

### Metrics
+ Assessment grade (featured article, good article, etc.)
+ Last 50 edits, grouped by editor
+ Category count
+ External links in the "External links" section
+ External links anywhere in the article
+ External links section count
+ Feedback score for completeness
+ Feedback score for objectivity
+ Feedback score for trustworthiness
+ Number of Google News results
+ Number of Google Web results
+ Image count
+ Incoming link count
+ Internal link count
+ Intro paragraph count
+ Page visits by date in the last month (according to http://stats.grok.se/)
+ Number of inline tags for POV statements
+ Number of inline tags for statements needing citation
+ Reference count
+ Reference section count
+ Likelihood the last revision was vandalism (according to http://www.wikitrust.net/)

## About
This tool was built by:

+ Ben Plowman
+ Mahmoud Hashemi
+ Sarah Nahm
+ Stephen LaPorte

...with help and food from the [awesome hosts of the hackathon](https://www.mediawiki.org/wiki/Hackathon)!

Copyright 2012, licensed under the GPL 3.0. See LICENSE.
