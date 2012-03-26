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

var basic_query = function(url, callback) {
    do_query(url, callback);
};

var yql_query = function(yql, format, callback) {
    var kwargs = {data: {q: yql, format: format}};
    do_query('http://query.yahooapis.com/v1/public/yql', callback, kwargs);
};

var base_input = function(name, query, process, complete) {
    var self = {};
    
    self.name = name;
    self.query = query;
    self.process = process;
    self.complete = complete;
    
    self.fetch_callback = function(data) {
        self.fetch_data = data; //may or may not be large
        var results = self.results = process(data);
        complete(self);
    };
    
    return self;
};

var web_input = function(name, url, process, complete) {
    var self = base_input(name, url, process, complete);
    self.url = self.query;
    
    do_query(url, self.fetch_callback);
    
    return self;
};

var yql_input = function(name, query, process, complete) {
    var self = base_input(name, query, process, complete);
    
    var kwargs = {data: {q: query, format: 'json'}};
    do_query('http://query.yahooapis.com/v1/public/yql', callback, kwargs);
    
    return self;
};

var Step = require('./step.js');

// One limitation on this model (easily refactored): calculators can't read from data
// they can only write to it. Mostly this is because we don't know what will or won't
// be present.

// TODO: refactor to allow inputs without fetches. pass in DOM/global-level input data
var make_evaluator = function(dom, rewards, callback) {

    var self          = {};
    var query_results = [];
    var callbacks     = [callback];
    
    self.article_title = article_title = dom.mw.config.get('wgTitle');
    self.article_id    = article_id    = dom.mw.config.get('wgArticleId');
    self.revision_id   = dom.mw.config.get('wgCurRevisionId');
    self.dom           = dom; // TODO rename to document for internal use?
    self.rewards = rewards;
    
    self.data    = {};
    self.results = null;
    self.inputs  = [];
    self.failed_inputs = [];
    
    Step(function register_inputs() {
        var results_group = this.group();
    
        // TODO these inputs could be callable objects. add a 'source' attribute to a function and add that as an input to the evaluator.
        
        self.add_input('editorStats', basic_query('http://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles=' + article_title + '&rvprop=user&rvlimit=50&format=json', results_group()), editorStats);
        self.add_input('inLinkStats', basic_query('http://en.wikipedia.org/w/api.php?action=query&format=json&list=backlinks&bltitle=' + article_title + '&bllimit=500&blnamespace=0', results_group()), inLinkStats);
        self.add_input('feedbackStats', basic_query('http://en.wikipedia.org/w/api.php?action=query&list=articlefeedback&afpageid=' + article_id + '&afuserrating=1&format=json&afanontoken=01234567890123456789012345678912', results_group()), feedbackStats);
        self.add_input('searchStats', basic_query('http://ajax.googleapis.com/ajax/services/search/web?v=1.0&q=' + article_title, results_group()), searchStats);
        self.add_input('newsStats', basic_query('http://ajax.googleapis.com/ajax/services/search/news?v=1.0&q=' + article_title, results_group()), newsStats);
        self.add_input('wikitrustStats', yql_query('select * from html where url ="http://en.collaborativetrust.com/WikiTrust/RemoteAPI?method=quality&revid=' + revision_id + '"', 'json', results_group()), wikitrustStats);
        self.add_input('grokseStats', yql_query('select * from json where url ="http://stats.grok.se/json/en/201201/' + article_title + '"', 'json'), grokseStats);
        self.add_input('getAssessment', basic_query('http://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles=Talk:' + article_title + '&rvprop=content&redirects=true&format=json', results_group()), getAssessment);
        self.add_input('domStats', null, domStats);
        
        for ( i in inputs ) {
            var save_callback = function(err, data) {
                try {
                    extend(self.data, input.calculate(data, self.dom));
                    input_done(input, data, calc_scores);
                } catch (real_err) {
                    input_done(input, {}, calc_scores);
                    self.failed_inputs.push(input);
                }
            };
        }
    }, function calculate_results(err, completed_inputs) {
        // handle 'err'
        // also manually check through the inputs
        //    - if an input has a error set, mark it as down
        // merge page_data
        // call calc_scores()
    }, function eval_complete(err) {
        //trigger complete() listeners
    };
    
    self.add_input = function(name, fetch, calculate) {
        // name is mostly for error messages/debugging
        // source is a callable that takes a callback
        // calculator is a callable that takes data from source and returns results
        var inputs = self.inputs,
            input = {'name':name, 'fetch':fetch, 'calculate':calculate};
        inputs.push(input);

        var save_callback = function(err, data) {
            try {
                extend(self.data, input.calculate(data, self.dom));
                input_done(input, data, calc_scores);
            } catch (real_err) {
                input_done(input, {}, calc_scores);
                self.failed_inputs.push(input);
            }
        };
        if (fetch) {
            input.fetch(save_callback);
        } else {
            save_callback(null, {}); // TODO clarify
        }
    };

    var complete_callback = function(page_data, rewards) {
        var fail_count = self.failed_inputs.length;

        if (fail_count > 0) {
            console.log('\nWarning: There were ' + fail_count + ' failed inputs.\n');
        }
        self.results = calc_scores(page_data, rewards);

        for(var i=0; i < callbacks.length; ++i) {
            callbacks[i](null, self); //call all the on_complete callbacks
        }
    };

    self.on_complete = function(callback) {
        callbacks.push(callback);
        // if the queries are complete, we need to manually trigger callback
        if (query_results.length == self.inputs.length && self.results) {
            callback(null, self);
        }
    };

    var input_done = function(input, data) {
        var tmp_results = [],
            inputs = self.inputs;

        input.data = data;
        for (var i = 0; i < inputs.length; ++i) {
            if (inputs[i].data !== undefined) {
                tmp_results.push(inputs[i].data);
            }
            // TODO add request failure handling
        }

        if (tmp_results.length == inputs.length) {
            query_results = tmp_results;
            console.log('all inputs done');
            complete_callback(self.data, self.rewards);
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

function domStats(data, dom) {
    var ret = {},
        $   = dom.jQuery;

    ret.ref_count = $('.reference').length;
    
    ret.paragraph_count = $('.mw-content-ltr p').length;
    ret.image_count = $('img').length;
    //ret.category_count = data.parse.categories.length -> dom.mw.config.get('categories').length;
    ret.reference_section_count = $('#References').length;
    ret.external_links_section_count = $('#External_links').length;
    ret.external_links_in_section = $('#External_links').parent().nextAll('ul').children().length;
    //ret.external_links_total = data.parse.externallinks.length;
    //ret.internal_links = data.parse.links.length;
    ret.intro_p_count =  $('.mw-content-ltr p').length;
    
    ret.ref_needed_count = $('span:contains("citation")').length;
    ret.pov_statement_count = $('span:contains("neutrality")').length;
    ret.pov_statement_count = $('span:contains("neutrality")').length;
    
    return ret;
}
domStats.type = 'yql';
domStats.url = 'http://';

inputs.push(create_yql_input('name', 'url $article_title ?sdfs', function(data) {

}, input_complete));

for (input in inputs) {
    input.start(group());
}

create_sql_input('query', function(data) {

});

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

    var ratings     = data.query.articlefeedback[0].ratings,
        trustworthy = ratings[0],
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
    ret.wikitrust = parseFloat(data.query.results.body.p);
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

function print_page_stats(err, ev) {
    console.log("\nPage stats for " + ev.article_title + "\n");
    for(var stat in ev.data) {
        console.log(stat + ': ' + ev.data[stat]);
    }


    console.log("\nResults for " + ev.article_title + "\n");
    for(var area in ev.results) {
        console.log(area + ': ' + ev.results[area].score + '/' + ev.results[area].max);
    }

    console.log("\nRecommendations for " + ev.article_title + "\n");
    var recos = ev.results.recos;
    for(var attr in recos) {
        console.log(attr + ': ' + recos[attr].cur_stat + ';' + recos[attr].points);
    }
}

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
        revision_id         = article_info.article_title,
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

function get_category(err, kwargs) {
    do_query('http://en.wikipedia.org/w/api.php?action=query&generator=categorymembers&gcmtitle=' + kw.name + '&prop=info&gcmlimit=' + kw.limit + '&format=json',
        function(err, data) {
            var page_keys = keys(data.query.pages),
                pages     = data.query.pages;

            for(var i=0; i < page_keys.length; ++i){
                if(pages[page_keys[i]].ns === 0) {
                    var article_title      = pages[page_keys[i]].title.replace(/\s/g,'_'),
                        article_id         = pages[page_keys[i]].pageid,
                        rev_id             = pages[page_keys[i]].lastrevid;

                    get_article(article_title, article_id, rev_id);
                }
            }
        });
}

Step(
    function start() {
        var kwargs = {'article_title':article_title};
        console.log("Start QV on "+article_title);
        get_article_info(null, kwargs, this.parallel()); //article title normalization?
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
        var ev = make_evaluator(window, rewards, this);
    },
    function all_done(err, evaluator) {
        if (err) {
            console.log('Could not evaluate article: '+err);
            throw err; //return //TODO how to give up?
        }
        console.log("Done QV on "+article_title);
        print_page_stats(err, evaluator);
    }
);
//var start = get_article_info;
//start(article_title);

//get_category('Category:Pokémon', 5);