/**
* Article quality visualization mediawiki gadget
*  for the San Francisco Mediawiki Hackathon, 2012
*  for more information, see https://www.mediawiki.org/wiki/January_2012_San_Francisco_Hackathon
* 
* By: Ben Plowman, Mahmoud Hashemi, Sarah Nahm, and Stephen LaPorte
* 
* Copyright 2012
* 
* This program is free software: you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.
* 
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
* 
* You should have received a copy of the GNU General Public License
* along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

// if this page is on a mediawiki site, change to testing to false:
var testing = true;


var page_stats = {};
var rewards = {};

if(testing == true) {
    var page_title = 'Charizard'; 
    var revid = 471874316; 
    var articleId = 60000; 
} else {
    var page_title = mw.config.get('wgTitle');
    var revid = mw.config.get('wgCurRevisionId');
    var articleId = mw.config.get('wgArticleId');
}

/*
* Metrics for article quality
*/
rewards['vetted'] = {}
rewards['vetted']['unique_authors'] = binStat(20, 40, 100);
rewards['vetted']['paragraph_count'] = rangeStat(10, 30, 100);
//rewards['vetted']['wikitrust_score'] = binStat(.;
// rewards.vetted.['visits_per_last_edit'] = ;
// rewards.vetted.['flags_total'] = ;

rewards.structure = {};
// rewards.structure.intro_paragraph = ;
rewards.structure.ref_section = binStat(1, 1, 100);
rewards.structure.external_links_total = binStat(10, 20, 100);
// rewards.structure.sections_per_link = binStat(;

rewards.richness = {};
// rewards.richness.length = ;
rewards.richness.image_count = binStat(2, 4, 100);
rewards.richness.external_links_total = binStat(10, 20, 100);
// rewards.richness.audio = ;
// rewards.geodata = ;

rewards.integrated = {};
rewards.integrated.category_count = binStat(3, 5, 100);
rewards.integrated.incoming_links = binStat(3, 50, 100);
rewards.integrated.outgoing_links = binStat(3, 50, 100);
//rewards.integrated.read_more_section = ;

rewards.community = {};
//rewards.community.assessment = ;
//rewards.community.visits_per_day = ;
rewards.community.unique_authors = binStat(20, 40, 100);
//rewards.community.visits_per_last_edit = ;
//rewards.community.flags_total = ;
//rewards.community.trustworthy = ;
//rewards.community.objective = ;
//rewards.community.complete = ;
//rewards.community.wellwritten = ;

rewards.citations = {};
//rewards.citations.reference_count_per_paragraph = ;
rewards.citations.ref_count = binStat(5, 10, 100);
//rewards.citations.citation_flag = ;

rewards.significance = {};
//rewards.significance.paragraph_per_web_results = {};
//rewrads.significance.paragraph_per_news_results = {};
//rewards.significance = binStat(;

function binStat(threshold, great, reward) {
	return {'type':'bin','threshold': threshold, 'great': great,'reward': reward};
}

function rangeStat(start, end, max_score) {
	return {'type':'range','start':start,'threshold':end,'reward':max_score};
}

function calculate(stats, rewards) {
	var area = keys(rewards), 
		result = {},
		val = 0;
	for(var i = 0; i < area.length; i++) {
		var attribs = keys(rewards[area[i]]);
		for(var j = 0; j < attribs.length; j++) {
			if(rewards[area[i]][attribs[j]].type == 'bin') {
				if(stats[attribs[j]] >= rewards[area[i]][attribs[j]].great) {
					val = rewards[area[i]][attribs[j]].reward;
				} else if(stats[attribs[j]] >= rewards[area[i]][attribs[j]].threshold) {
					val = rewards[area[i]][attribs[j]].reward * .7; 
				}
			} else if (rewards[area[i]][attribs[j]].type == 'range') {
				var slope = rewards[area[i]][attribs[j]].reward / rewards[area[i]][attribs[j]].start;
				if(stats[attribs[j]] < rewards[area[i]][attribs[j]].start){
					val = (stats[attribs[j]]) * slope;
				} else if(stats[attribs[j]] > rewards[area[i]][attribs[j]].threshold){
					val = (rewards[area[i]][attribs[j]].reward - (stats[attribs[j]] - rewards[area[i]][attribs[j]].threshold)) * slope;
					val = Math.max(0, val);
				} else {
					val = rewards[area[i]][attribs[j]].reward;	
				}
			}
			
		
		result[area[i]] = result[area[i]] || {};
		result[area[i]].score = result[area[i]].score + val || val;
		result[area[i]].max = result[area[i]].max + rewards[area[i]][attribs[j]].reward || rewards[area[i]][attribs[j]].reward;

		result['total'] = result['total'] || {};
		result['total'].score = result['total'].score + val || val;
		result['total'].max = result['total'].max + rewards[area[i]][attribs[j]].reward || rewards[area[i]][attribs[j]].reward;	
		}
	}
	return result;
}

function doQuery(url, success_callback, name, kwargs) {
    name = name || url;
    var all_kwargs = {
        url: url,
        dataType: 'jsonp',
        success: function(data) {
            queryResults[name] = data;
            success_callback(data);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            queryResults[name] = false;
            console.log('jqXHR: ' + jqXHR + ', textStatus: ', + textStatus + ', errorThrown: ' + errorThrown);
        },
        complete: function() {
            $(document).trigger(name+'-complete');
        }
    };
    
    for (key in kwargs) {
        if(kwargs.hasOwnProperty(key)) {
            all_kwargs[key] = kwargs[key];
        }
    }
    $.ajax(all_kwargs);
}
var queryResults = {}, 
    queryRegister = [];
    
    
function registerQuery(name, url, success_callback, kwargs) {
    queryRegister.push({'name':name,'url':url, 'callback':success_callback, 'kwargs':kwargs});
}

var queriesComplete = false;
function doAllQueries(success_callback) {
    if (queriesComplete) {
        return;
    }
    for(var i = 0; i < queryRegister.length; i++) {
        var name   = queryRegister[i].name,
            url    = queryRegister[i].url,
            kwargs = queryRegister[i].kwargs;
        $(document).bind(name+'-complete', function() {
            for(var j=0; j < queryRegister.length; j++) {
                if(! queryResults.hasOwnProperty(queryRegister[j].name)) {
                    return false;
                }
            }
            queriesComplete = true;
            success_callback();
        });
        doQuery(url, function(){return;}, name, kwargs);
    }
}

registerQuery('domStats', 'http://en.wikipedia.org/w/api.php?action=parse&page=' + page_title + '&format=json&callback=?');
registerQuery('editorStats', 'http://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles=' + page_title + '&rvprop=user&rvlimit=50&format=json&callback=?');
registerQuery('inLinkStats', 'http://en.wikipedia.org/w/api.php?action=query&format=json&list=backlinks&bltitle=' + page_title + '&bllimit=500&blnamespace=0&callback=?');
//registerQuery('feedbackStats', 'http://en.wikipedia.org/w/api.php?action=query&list=articlefeedback&afpageid=' + page_id + '&afuserrating=1&format=json&callback=?&afanontoken=01234567890123456789012345678912');
registerQuery('searchStats', 'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&q=' + page_title);
registerQuery('newsStats', 'http://ajax.googleapis.com/ajax/services/search/news?v=1.0&q=' + page_title);
registerQuery('wikitrustStats', 'http://query.yahooapis.com/v1/public/yql', null, {data : {q : 'select * from html where url ="http://en.collaborativetrust.com/WikiTrust/RemoteAPI?method=quality&revid=' + revid + '"',format : 'json'}});


function domStats(data) {
    var wikitext = data['parse']['text']['*'];
    page_stats['ref_count'] = $('.reference', wikitext).length;
    page_stats['paragraph_count'] = $('.mw-content-ltr p').length;
    page_stats['image_count'] = $('img', wikitext).length;
    page_stats['category_count'] = data['parse']['categories'].length;
    page_stats['reference_section_count'] = $('#References', wikitext).length;
    page_stats['external_links_section_count'] = $('#External_links', wikitext).length;
    page_stats['external_links_in_section'] = $('#External_links', wikitext).parent().nextAll('ul').children().length;
    page_stats['external_links_total'] = data['parse']['externallinks'].length;
    page_stats['internal_links'] = data['parse']['links'].length;

}

function editorStats(data) {
	for(var id in data['query']['pages']) {
		var author_counts = {};
		if(!data['query']['pages'].hasOwnProperty) {
			continue;
		}
		var editor_count = data['query']['pages'][id]['revisions'];
		for(var i = 0; i < editor_count.length; i++) {
			if(!author_counts[editor_count[i].user]) {
				author_counts[editor_count[i].user] = 0;
			}
			author_counts[editor_count[i].user] += 1;
		}
		page_stats.author_counts = author_counts;
	}
    page_stats.unique_authors = keys(page_stats.author_counts).length;
}


function inLinkStats(data) {
                //TODO: if there are 500 backlinks, we need to make another query
    page_stats['incoming_links'] = data['query']['backlinks'].length;
}

function feedbackStats(data) {
    var ratings = data['query']['articlefeedback'][0]['ratings'];
    var trustworthy = ratings[0];
    var objective = ratings[1];
    var complete = ratings[2];
    var wellwritten = ratings[3];

    page_stats['trustworthy'] = trustworthy['total'] / trustworthy['count'];
    page_stats['objective'] = objective['total'] / objective['count'];
    page_stats['complete'] = complete['total'] / complete['count'];
    page_stats['wellwritten'] = wellwritten['total'] / wellwritten['count'];
}

function searchStats(data) {
    page_stats['google_search_results'] = parseInt(data['responseData']['cursor']['estimatedResultCount']);
}

function newsStats(data) {
    page_stats['google_news_results'] = parseInt(data['responseData']['cursor']['estimatedResultCount']);
}

function keys(obj) {
    return $.map(obj, function(value, key) {
        return key;
    })  
}

function wikitrustStats(data) {
    console.log(data);
}

var score = {};
      
function ollKomplete(){
    domStats(queryResults['domStats']);	
    //feedbackStats(queryResults['feedbackStats']);
    editorStats(queryResults['editorStats']);	
    inLinkStats(queryResults['inLinkStats']);	
    searchStats(queryResults['searchStats']);	
    newsStats(queryResults['newsStats']);
    wikitrustStats(queryResults['wikitrustStats']);
    score = calculate(page_stats, rewards);
    var ratio = (score.total.score+0.0)/score.total.max;
    
    var percent = Math.round(ratio * 100);
    $('div.top').css('width', percent+'px');
    $('div.bottom').css('width', (100-percent)+'px');
    $('#overall_percent').text(percent+'%');

    if(testing == true) {
        $('#testingHeading').append(page_title)
    }
}    

$(document).ready(function() {

    doAllQueries(ollKomplete);

    $("#bodyContent").prepend("<div id='quality'><div class='quality_bar'></div></div>");
    var box = $('#quality');
    var bar = $('.quality_bar');

    bar.append('<div><p class="bar_text">Overall quality: </p></div><div id="overall_graph"><div class="top"></div><div class="bottom"></div></div><div class="headline" id="overall_percent"></div>');
    bar.append('<div><p class="bar_text">Improve this score by adding: </p><p class="list"><p>...</p></div>')

});