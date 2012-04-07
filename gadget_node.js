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

 // TODO: contextualized inputs
 // TODO: pass in precomputed data
 // TODO: save/replay queue?
 
// if this page is on a mediawiki site, change to testing to false:
var testing = true;


if(testing === true) {
    var article_title = 'Charizard';
    //var revid = 476545765;
    //var articleId = 7463;
} else {
    var article_title = mw.config.get('wgTitle');
    var revid = mw.config.get('wgCurRevisionId');
    var articleId = mw.config.get('wgArticleId');
}

// Convenience functions for reward formulae
function overStat(threshold, great, reward) {
    return {'type':'over','threshold': threshold, 'great': great,'reward': reward};
}

function underStat(threshold, great, reward) {
    return {'type':'under', 'threshold': threshold, 'great': great, 'reward': reward};
}

function rangeStat(start, end, max_score) {
    return {'type':'range','start':start,'threshold':end,'reward':max_score};
}

/*
 * Metrics for article quality
 */
var rewards = {
    'vetted': {
        'unique_authors'        : overStat(20, 40, 200),
        'paragraph_count'       : rangeStat(10, 30, 100),
        'wikitrust'             : underStat(0.6, 0.45, 600)
    },
    // rewards.vetted.['visits_per_last_edit'] = ;
    // rewards.vetted.['flags_total'] = ;
    'structure': {
        'ref_section'           : overStat(1, 1, 100),
        'external_links_total'  : overStat(10, 20, 200)
    },
    // rewards.structure.intro_paragraph = ;
    // rewards.structure.sections_per_link = overStat(;
    'richness': {
        'image_count'           : overStat(5, 7, 300),
        'external_links_total'  : overStat(10, 20, 100)
    },
    // rewards.richness.length = ;
    // rewards.richness.audio = ;
    // rewards.geodata = ;
    'integrated': {
        'category_count'        : overStat(15, 30, 100),
        'incoming_links'        : overStat(3, 50, 100),
        'outgoing_links'        : overStat(3, 50, 100),
        'internal_links'        : overStat(100, 200, 400)
    },
    //rewards.integrated.read_more_section = ;
    'community': {
        'unique_authors'        : overStat(20, 40, 100),
        'fbTrustworthy'         : overStat(3, 3.5, 100),
        'fbObjective'           : overStat(3, 3.5, 100),
        'fbComplete'            : overStat(3, 3.5, 100),
        'fbWellwritten'         : overStat(3, 3.5, 100)
    },
    //rewards.community.assessment = ;
    //rewards.community.visits_per_day = ;
    //rewards.community.visits_per_last_edit = ;
    //rewards.community.flags_total = ;
    'citations': {
        'ref_count'             : overStat(100, 300, 100),
        'ref_needed_count'      : underStat(5, 0, 100),
        'pov_statement_count'   : underStat(2, 0, 100)

    },
    //rewards.citations.reference_count_per_paragraph = ;
    //rewards.citations.citation_flag = ;
    'significance': {

    }
    //rewards.significance.paragraph_per_web_results = {};
    //rewrads.significance.paragraph_per_news_results = {};
    //rewards.significance = overStat(;
};

function keys(obj) {
    var ret = [];
    for(var k in obj) {
        if (obj.hasOwnProperty(k)) {
            ret.push(k);
        }
    }
    return ret;
}

var dummy_window = require('jsdom').jsdom().createWindow();
dummy_window.XMLHttpRequest = require('xmlhttprequest').XMLHttpRequest;
var $ = require('jquery').create(dummy_window);
    $.support.cors = true;
var extend = $.extend;

var global_timeout = 8000;

function do_query(url, complete_callback, kwargs) {
    var all_kwargs = {
        url: url,
        type: 'get',
        dataType: 'json',
        timeout: global_timeout, // TODO: convert to setting. Necessary to detect jsonp error.
        success: function(data) {
            complete_callback(null, data);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            complete_callback(errorThrown, null);
        },
        complete: function(jqXHR, textStatus) {
            // TODO: error handling (jsonp doesn't get error() calls for a lot of errors)
        },
        headers: { 'User-Agent': 'QualityVis/0.0.0 Mahmoud Hashemi makuro@gmail.com' }
    };

    for (var key in kwargs) {
        if(kwargs.hasOwnProperty(key)) {
            all_kwargs[key] = kwargs[key];
        }
    }
    $.ajax(all_kwargs);
}

function debounce(fn, delay) {
    var timer = null;
    return function () {
        var context = this, args = arguments;
        clearTimeout(timer);
        timer = setTimeout(function () {
            fn.apply(context, args);
        }, delay);
    };
}

function throttle(fn, delay) {
    var timer = null;
    return function () {
        var context = this, args = arguments;
        timer = setTimeout(function () {
            fn.apply(context, args);
        }, delay);
    };
}

// TODO: register/save function?
var queue = function(delay) {
    delay = delay || 250;
    var self = {};
    var process, timer;
    self.pending = [];
    self.enqueue = function(func, callback) {
        self.pending.push({'func':func, 'callback':callback});
        //console.log('enqueueing an n');
        self.start();
    };
    self.stop = function() {
        //console.log('stopped');
        clearTimeout(timer);
        timer = null;
    };
    self.start = function() {
        if (!timer) {
            //console.log('started');
            timer = setInterval(process, delay);
            process();
        }
    };
    process = function process_task() {
        //console.log('attempting to process...');
        if(self.pending.length > 0) {
            var n = self.pending.pop();
            //console.log('doin an n');
            var retry = function retry() {
                self.enqueue(n.func, n.callback);
            };
            n.func(n.callback, retry);
        } else {
            self.stop();
        }
    };
    return self;
};

// TODO configurable retry failure. at least retry in a couple seconds.
// complete is called on the input actually completely finishing (success/fatal error)
// ind_complete is called for an individual call's completion (retry)
var input = function(name, fetch, process) {
    var self;
    self = function(complete, retry) {
        //console.log('Calling into input: '+name);
        var fetch_callback = function fetch_callback(err, data) {
            self.fetch_data = data; //may or may not be large
            if (err) {
                console.log('failed fetch on: '+name+' '+err);
                self.error = 'Failed to fetch data for '+name;
                complete(null, self);  // err?
            }
            
            try {
                self.results = process(data);
            } catch (proc_err) {
                self.results = null;
                self.error = 'Failed to process data for '+name;
                console.log(self.error);
            }
            complete(null, self);
        };
        
        if (fetch instanceof Function) {
            fetch(fetch_callback);
        } else {
            fetch_callback(null, fetch);
        }
    };
    self.name     = name;
    self.attempts = 0;
    
    return self;
};

var web_source = function(url) {
    var self = function fetch_web_source(callback) {
        //console.log('start web query for '+name);
        do_query(url, callback);
    };
    self.get_url = function get_url() {
        return url;
    };
    return self;
};

var yql_source = function(query) {
    return function fetch_yql_source(callback) {
        //console.log('start yql query for '+name);
        var kwargs = {data: {q: query, format: 'json'}};
        do_query('http://query.yahooapis.com/v1/public/yql', callback, kwargs);
    };
};

var Step = require('./step.js');

// One limitation on this model (easily refactored): calculators can't read from data
// they can only write to it. Mostly this is because we don't know what will or won't
// be present.

// TODO: refactor to allow inputs without fetches. pass in DOM/global-level input data
var make_evaluator = function(dom, rewards, callback, mq) {

    var self          = {};
    var query_results = [];
    var callbacks     = [callback];
    
    self.article_title = article_title = dom.mw.config.get('wgTitle');
    self.article_id    = article_id    = dom.mw.config.get('wgArticleId');
    self.revision_id   = revision_id   = dom.mw.config.get('wgCurRevisionId');
    self.dom           = dom; // TODO rename to document for internal use?
    self.rewards = rewards;
    
    self.data    = {};
    self.results = null;
    self.failed_inputs = [];
    
    Step(function register_inputs() {
        var results_group = this.group();
        self.inputs  = [
             input('editorStats', web_source('http://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles=' + article_title + '&rvprop=user&rvlimit=50&format=json'), editorStats)
            ,input('inLinkStats', web_source('http://en.wikipedia.org/w/api.php?action=query&format=json&list=backlinks&bltitle=' + article_title + '&bllimit=500&blnamespace=0'), inLinkStats)
            ,input('feedbackStats', web_source('http://en.wikipedia.org/w/api.php?action=query&list=articlefeedback&afpageid=' + article_id + '&afuserrating=1&format=json&afanontoken=01234567890123456789012345678912'), feedbackStats)
            ,input('searchStats', web_source('http://ajax.googleapis.com/ajax/services/search/web?v=1.0&q=' + article_title), searchStats)
            ,input('newsStats',  web_source('http://ajax.googleapis.com/ajax/services/search/news?v=1.0&q=' + article_title), newsStats)
            ,input('wikitrustStats', yql_source('select * from html where url ="http://en.collaborativetrust.com/WikiTrust/RemoteAPI?method=quality&revid=' + revision_id + '"'), wikitrustStats)
            ,input('grokseStats', yql_source('select * from json where url ="http://stats.grok.se/json/en/201201/' + article_title + '"'), grokseStats)
            ,input('getAssessment', web_source('http://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles=Talk:' + article_title + '&rvprop=content&redirects=true&format=json'), getAssessment)
            
            ,input('domStats', dom, domStats)
        ];
        
        for(var i=0; i<self.inputs.length; ++i) {
            mq.enqueue(self.inputs[i], results_group());
            //self.inputs[i]();
        }
        
    }, function calculate_results(err, completed_inputs) {
        if (err) {
            console.log('One or more inputs failed: ' + err);
            throw err;
        }
        
        var merged_data = {};
        for (var i = 0; i < completed_inputs.length; ++i) {
            var cur_input = completed_inputs[i];
            if (cur_input.error) {
                console.log('Input failed: '+ cur_input.name + ' with error: ' + cur_input.error);
                self.failed_inputs.push(cur_input);
            } else {
                //console.log('Input succeeded: '+cur_input.name);
                for (var prop in cur_input.results) {
                    merged_data[prop] = cur_input.results[prop];
                }
            }
        }
        self.data = merged_data;
        return merged_data;
    }, function eval_complete(err, page_data) {
        if (err) {
            throw err;
        }
        var fail_count = self.failed_inputs.length;

        if (fail_count > 0) {
            console.log('\nWarning: There were ' + fail_count + ' failed inputs.\n');
        }
        self.results = calc_scores(page_data, rewards);

        for(var i=0; i < callbacks.length; ++i) {
            callbacks[i](null, self); //call all the on_complete callbacks
        }
    });
    
    self.on_complete = function(callback) {
        callbacks.push(callback);
        // if the queries are complete, we need to manually trigger callback
        if (query_results.length == self.inputs.length && self.results) {
            callback(null, self);
        }
    };

    var calc_scores = function(stats, rewards) {
        var result = {};

        result.recos = {};

        for(var area in rewards) {
            for(var attr in rewards[area]) {
                var r = rewards[area][attr], // reward structure for this area/attr combo

                    s = stats[attr], // page stat for this attribute
                    val = 0;

                if (!r || !s) {
                    continue;
                }

                if(r.type == 'over') {
                    if( s >= r.great ) {
                            val = r.reward;
                    } else if ( s >= r.threshold ) {
                            val = r.reward * 0.7; // TODO: make tuneable?
                    }
                } else if (r.type == 'under') {
                    if( s < r.great ) {
                                val = r.reward;
                    } else if ( s < r.threshold ) {
                                val = r.reward * 0.7; // TODO: make tuneable?
                    }
                } else if (r.type === 'range') {
                    var slope = r.reward / r.start;
                    if( s < r.start) {
                            val = s * slope;
                    } else if( s > r.threshold){
                            val = r.reward - ((s - r.threshold) * slope);
                            val = Math.max(0, val);
                    } else {
                            val = r.reward;
                    }
                }
                if (val < r.reward) {
                    result.recos[attr] = result.recos[attr] || {};

                    var gain = r.reward - val;
                    result.recos[attr].points    = result.recos[attr].points + gain || gain;
                    result.recos[attr].cur_stat  = s;
                }

                result[area]       = result[area] || {};
                result[area].score = result[area].score + val || val;
                result[area].max   = result[area].max + r.reward || r.reward;

                result.total       = result.total || {};
                result.total.score = result.total.score + val || val;
                result.total.max   = result.total.max + r.reward || r.reward;
            }
        }
        return result;
    };

    
    return self;
};

function domStats(dom) {
    var ret = {},
        $   = dom.jQuery;

    ret.ref_count = $('.reference').length; /* includes both references and notes */
    ret.source_count = $('li[id^="cite_note"]').length; /* includes both references and notes */
    ret.word_count = $('p').text().split(/\b[\s,\.-:;]*/).length;
    ret.paragraph_count = $('p').length;
    ret.paragraph_counts = [];
    $('p').each(function() {
        ret.paragraph_counts.push($(this).text().split(/\b[\s,\.-:;]*/).length);
    });
    ret.image_count = $('img').length;
    //ret.category_count = dom.mw.config.get('wgCategories').length;
    ret.reference_section_count = $('#References').length;
    ret.external_links_section_count = $('#External_links').length;
    ret.external_links_in_section = $('#External_links').parent().nextAll('ul').children().length;
    //ret.external_links_total = data.parse.externallinks.length;
    //ret.internal_links = data.parse.links.length;
    ret.intro_p_count =  $('p').length;
    ret.p_count = $('p').length;
    ret.new_internal_link_count = $('.new');
    ret.ref_needed_count = $('span:contains("citation")').length;
    ret.pov_statement_count = $('span:contains("neutrality")').length;
    ret.pov_statement_count = $('span:contains("neutrality")').length;
    ret.dom_internal_link_count = $('p a:not([class])[href^="/wiki/"]').length;
    ret.first_head_count = $('h2').length;
    ret.second_head_count = $('h3').length;
    ret.links = [];
    $('p a:not([class])[href^="/wiki/"]').each(function() {
        ret.links.push($(this).text());
    });
    ret.dom_category_count = $("a[href^='/wiki/Category:']").length;

    /* templates will (most likely) be 0 or 1 */
    ret.templ_delete = $('.ambox-delete').length;
    ret.templ_autobiography = $('.ambox-autobiography').length; // Template:Autobiography
    ret.templ_advert = $('.ambox-Advert').length; // Template:Advert
    ret.templ_citation_style = $('.ambox-citation_style').length; // Template:Citation style
    ret.templ_cleanup = $('.ambox-Cleanup').length;
    ret.templ_COI = $('.ambox-COI').length;
    ret.templ_confusing = $('.ambox-confusing').length;
    ret.templ_context = $('.ambox-Context').length;
    ret.templ_copy_edit = $('.ambox-Copy_edit').length;
    ret.templ_dead_end = $('.ambox-dead_end').length;
    ret.templ_disputed = $('.ambox-disputed').length;
    ret.templ_essay_like = $('.ambox-essay-like').length;
    ret.templ_expert = $("td:contains('needs attention from an expert')").length; // Template:Expert
    ret.templ_fansight = $('td:contains("fan\'s point of view")').length;
    ret.templ_globalize = $('td:contains("do not represent a worldwide view")').length;
    ret.templ_hoax = $('td:contains("hoax")').length;
    ret.templ_in_universe = $('.ambox-in-universe').length;
    ret.templ_intro_rewrite = $('.ambox-lead_rewrite').length;
    ret.templ_merge = $('td:contains("suggested that this article or section be merged")').length;
    ret.templ_no_footnotes = $('.ambox-No_footnotes').length;
    ret.templ_howto = $('td:contains("contains instructions, advice, or how-to content")').length;
    ret.templ_non_free = $('.ambox-non-free').length;
    ret.templ_notability = $('.ambox-Notability').length;
    ret.templ_not_english = $('.ambox-not_English').length;
    ret.templ_NPOV = $('.ambox-POV').length;
    ret.templ_original_research = $('.ambox-Original_research').length;
    ret.templ_orphan = $('.ambox-Orphan').length;
    ret.templ_plot = $('.ambox-Plot').length;
    ret.templ_primary_sources = $('.ambox-Primary_sources').length;
    ret.templ_prose = $('.ambox-Prose').length;
    ret.templ_refimprove = $('.ambox-Refimprove').length;
    ret.templ_sections = $('.ambox-sections').length;
    ret.templ_tone = $('.ambox-Tone').length;
    ret.templ_tooshort = $('.ambox-lead_too_short').length;
    ret.templ_style = $('.ambox-style').length;
    ret.templ_uncategorized = $('.ambox-uncategorized').length;
    ret.templ_update = $('.ambox-Update').length;
    ret.templ_wikify = $('.ambox-Wikify').length;

    /* may return 0+ (more = worse) */
    ret.templ_multiple_issues = $('.ambox-multiple_issues li').length;

    return ret;
}

// Start calculation functions
function editorStats(data) {
    var ret = {};
    for(var id in data.query.pages) {
        if(!data.query.pages.hasOwnProperty(id)) {
        continue;
        }
        var author_counts = {};
        var editor_count = data.query.pages[id].revisions;
        for(var i = 0; i < editor_count.length; i++) {
            if(!author_counts[editor_count[i].user]) {
                    author_counts[editor_count[i].user] = 0;
            }
            author_counts[editor_count[i].user] += 1;
        }
        ret.author_counts = author_counts;
    }
    ret.unique_authors = keys(ret.author_counts).length;

    return ret;
}

function inLinkStats(data) {
    //TODO: if there are 500 backlinks, we need to make another query
    var ret = {};
    ret.incoming_links = data.query.backlinks.length;
    return ret;
}
    
function feedbackStats(data) {
    var ret = {};
    
    var ratings     = data.query.articlefeedback[0].ratings;
    if (!ratings) {
        return ret;
    }
    var trustworthy = ratings[0],
        objective   = ratings[1],
        complete    = ratings[2],
        wellwritten = ratings[3];

    ret.fbTrustworthy = trustworthy.total / trustworthy.count;
    ret.fbObjective = objective.total / objective.count;
    ret.fbComplete = complete.total / complete.count;
    ret.fbWellwritten = wellwritten.total / wellwritten.count;

    return ret;
}

function searchStats(data) {
    var ret = {};
    ret.google_search_results = parseInt(data.responseData.cursor.estimatedResultCount, 10);
    return ret;
}

function newsStats(data) {
    var ret = {};
    ret.google_news_results = parseInt(data.responseData.cursor.estimatedResultCount, 10);
    return ret;
}

function wikitrustStats(data) {
    var ret = {};
    var res = data.query.results.body.p;
    var success = !(res.indexOf('EERROR') == 0);
    if (success) {
        ret.wikitrust = parseFloat(res)
    }
    return ret;
}

function grokseStats(data) {
    var ret = {};
    ret.pageVisits = data.query.results.json;
    return ret;
}

function getAssessment(data) {
    var ret = {};
    var id      = keys(data.query.pages)[0],
        text    = (data.query.pages[id].revisions['0']['*']);

    /* From the 'metadata' gadget
     * @author Outriggr - created the script and used to maintain it
     * @author Pyrospirit - currently maintains and updates the script
     */
    var rating = 'none';
    if (text.match(/\|\s*(class|currentstatus)\s*=\s*fa\b/i))
    rating = 'fa';
    else if (text.match(/\|\s*(class|currentstatus)\s*=\s*fl\b/i))
    rating = 'fl';
    else if (text.match(/\|\s*class\s*=\s*a\b/i)) {
    if (text.match(/\|\s*class\s*=\s*ga\b|\|\s*currentstatus\s*=\s*(ffa\/)?ga\b/i))
            rating = 'a/ga'; // A-class articles that are also GA's
    else rating = 'a';
    } else if (text.match(/\|\s*class\s*=\s*ga\b|\|\s*currentstatus\s*=\s*(ffa\/)?ga\b|\{\{\s*ga\s*\|/i) &&
              !text.match(/\|\s*currentstatus\s*=\s*dga\b/i))

        rating = 'ga';
    else if (text.match(/\|\s*class\s*=\s*b\b/i))
    rating = 'b';
    else if (text.match(/\|\s*class\s*=\s*bplus\b/i))
    rating = 'bplus'; // used by WP Math
    else if (text.match(/\|\s*class\s*=\s*c\b/i))
    rating = 'c';
    else if (text.match(/\|\s*class\s*=\s*start/i))
    rating = 'start';
    else if (text.match(/\|\s*class\s*=\s*stub/i))
    rating = 'stub';
    else if (text.match(/\|\s*class\s*=\s*list/i))
    rating = 'list';
    else if (text.match(/\|\s*class\s*=\s*sl/i))
    rating = 'sl'; // used by WP Plants
    else if (text.match(/\|\s*class\s*=\s*(dab|disambig)/i))
    rating = 'dab';
    else if (text.match(/\|\s*class\s*=\s*cur(rent)?/i))
    rating = 'cur';
    else if (text.match(/\|\s*class\s*=\s*future/i))
    rating = 'future';
    ret.assessment = rating;

    return ret;
}

// End calculation functions

function get_article_info(err, kwargs, callback) {
    var article_title = kwargs.article_title;
    
    do_query('http://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles='+article_title+'&rvprop=ids&redirects=true&format=json',
        function(err, data) {
            if (err) {
                console.log('probably timed out');
            }
            var page_ids = keys(data.query.pages),
                pages    = data.query.pages;
            if (page_ids.length > 0) {
                var article_id    = page_ids[0];
                    article_title = pages[article_id].title.replace(' ', '_');
                    rev_id        = pages[article_id].revisions[0].revid;
                    prev_rev_id   = pages[article_id].revisions[0].parentid;
                callback(null, {'article_title':article_title,
                              'article_id':article_id,
                              'rev_id': rev_id});
                
            } else {
                console.log('No article with title '+ article_title + ' found.');
            }
        });
}

function get_article(err, kwargs, callback) {
    var article_title = kwargs.article_title;
    
    do_query('http://en.wikipedia.org/w/api.php?action=parse&page='+article_title+'&format=json&redirects=true',
         callback
    );
}

function prepare_window_node(err, kwargs, callback) {
    var data                = kwargs.data,
        article_info        = kwargs.article_info,
        article             = kwargs.article,
        article_title       = article_info.article_title,
        article_id          = article_info.article_id,
        revision_id         = article_info.rev_id,
        text                = article.parse.text['*'];
    
    var jsdom = require('jsdom');
    
    jsdom.env({
        html: text,
        done: function(errors, window) {
            var $ = require('jquery').create(window);
        
            var real_values = {
                'wgTitle': article_title,
                'wgArticleId': article_id,
                'wgCurRevisionId': revision_id
            };

            var mw = {}; //building a mock object to look like mw (loaded on wikipedia by javascript)
            mw.config = {};
            mw.config.get = function(key) {
                return real_values[key] || null;
            };
            window.mw = mw; //attach mock object to fake window
            callback(null, window);
        }
    });
}

function get_category(name, limit) {
    console.log('getting up to '+limit+' articles for '+name);
    Step( function get_article_names() {
        do_query('http://en.wikipedia.org/w/api.php?action=query&generator=categorymembers&gcmtitle=' + name + '&prop=info&gcmlimit=' + limit + '&format=json',
            this);
        }, function evaluate_articles(err, data) {
            if (err) {
                console.log('Could not retrieve category list: '+name+'.');
                throw err;
            }
            console.log('did the category query');
            var pages = data.query.pages;
            var infos = [];
            for(var key in pages){
                var page = pages[key];
                if(page.ns === 0) {
                    infos.push({'article_title': page.title.replace(/\s/g,'_'),
                                'article_id'   : page.pageid,
                                'rev_id'       : page.lastrevid
                                });
                }
            }
            console.log(infos.length + ' infos got.');
            var articles_group = this.group();
            for (var i=0; i < infos.length; ++i) {
                var article_title = infos[i].article_title,
                    article_id    = infos[i].article_id,
                    rev_id        = infos[i].rev_id;
                evaluate_article_node(article_title, article_id, rev_id, articles_group());
            }
        }, function output_evaluations(err, evs) {
            if (err) {
                throw err
            }
            //output_csv('yup.csv', evs);
            console.log(evs);
        });
}

function print_page_stats(err, ev) {
    console.log("\nPage stats for " + ev.article_title + "\n");
    for(var stat in ev.data) {
        console.log('  - '+stat + ': ' + ev.data[stat]);
    }


    console.log("\nResults for " + ev.article_title + "\n");
    for(var area in ev.results) {
        console.log('  - '+area + ': ' + ev.results[area].score + '/' + ev.results[area].max);
    }

    console.log("\nRecommendations for " + ev.article_title + "\n");
    var recos = ev.results.recos;
    for(var attr in recos) {
        console.log('  - '+attr + ': ' + recos[attr].cur_stat + ';' + recos[attr].points);
    }
}

var mq = queue(50);

var evaluators = [];

function escape_field(str) {
    return str;
}

function is_outputtable(val) {
    var val_type = typeof val;
    return !(val_type === 'function' || val_type === 'object');
}

var article_deets = ['article_title', 'article_id', 'revision_id'];
function output_csv(path, evs, callback) {
    //TODO: add run date, other metadata in csv comment
    //TODO: use async?
    //construct superset of stats for column headings
    var col_names, tmp_names = {};
    for (var i=0; i<evs.length; ++i) {
        var ev = evs[i];
        for (var stat in ev.data) {
            tmp_names[stat] = true;
        }
    }
    for (var i=0; i<tmp_names.length; ++i) {
        var do_output = false;
        var stat = tmp_names[i];
        for (var j=0; i<evs.length; ++i) {
            var ev = evs[j];
            if (is_outputtable(ev[stat])) {
                do_output = true;
            }
        }
        if (!do_output) {
            delete tmp_names[stat];
        }
    }
    var col_names = [];
    col_names.push.apply(col_names, article_deets);
    col_names.push.apply(col_names, keys(tmp_names).sort());
    
    var fs       = require('fs');
    var out_file = fs.createWriteStream(path, {'flags': 'w'});
    if (typeof out_file.setEncoding === 'function') {
        out_file.setEncoding('utf-8');
    }
    
    out_file.write(col_names.join(','));
    out_file.write('\n');
    for (var i=0; i<evs.length; ++i) {
        var ev = evs[i];
        for (var j=0; j<col_names.length; ++j) {
            var col_name = col_names[j];
            var cur_stat = ev.data[col_name] || ev[col_name];
            var to_write = cur_stat ? escape_field(cur_stat) : '';
            if (is_outputtable(cur_stat)) {
                out_file.write(to_write);
            } else {
                out_file.write('(object)');
            }
            out_file.write(',');
        }
        out_file.write('\n');
    }
    out_file.destroySoon();
    //callback();
}

function evaluate_article_node(article_title, article_id, rev_id, callback) {
    Step(
        function start() {
            var kwargs = {'article_title':article_title};
            console.log("Start QV on "+article_title);
            
            var info_callback = this.parallel();
            if (!article_id || !rev_id) {
                get_article_info(null, kwargs, info_callback); //article title normalization?
            } else {
                info_callback(null, { 'article_title': article_title,
                                    'article_id'   : article_id,
                                    'rev_id'       : rev_id
                                  });
            }
            get_article(null, kwargs, this.parallel());
        },
        function prepare_window(err, article_info, article_content) {
            if (err) {
                console.log('Error retrieving info for article "'+article_info.article_title+'"');
                throw err; //return //TODO how to give up?
            }
            prepare_window_node(err, {'article_info': article_info, 'article': article_content},
                                this);
        },
        function make_evaluator_wrapper(err, window) {
            if (err) {
                console.log('Could not construct window: '+err);
                throw err;
            }
            var ev = make_evaluator(window, rewards, this, mq);
        },
        function all_done(err, evaluator) {
            if (err) {
                console.log('Could not evaluate article: '+err);
                throw err; //return //TODO how to give up?
            }
            console.log('finished '+evaluator.article_title);
            //print_page_stats(err, evaluator);
            if (callback) {
                callback(null, evaluator);
            }
        }
    );
}
//get_category('Category:FA-Class_articles', 50);
get_category('Category:Articles_with_inconsistent_citation_formats', 2);