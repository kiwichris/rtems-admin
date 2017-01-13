/*!
 * Catalogue 0.1
 * Copyright 2017 Chris Johns <chrisj@rtems.org>
 * Licensed under the MIT license
 */

function catalogueHeader(id, title, date) {
    return '' +
	' <div class="table-responsive">' +
        '  <table class="table table-hover table-condensed table-nonfluid">' +
	'   <tbody>' +
	'    <thead>' +
	'     <tr id="' + id + '" class="accordion-toggle" data-toggle="collapse"' +
	'         data-parent="#rtems-catalogue" data-target=".' + id + 'Details">' +
	'      <th><span class="label label-default">' + date + '</span> ' + title + '</th>\n' +
	'      <th><i class="indicator glyphicon glyphicon-chevron-up pull-right"></i></th>' +
	'     </tr>' +
	'    </thead>' +
	'    <tr>' +
	'     <td colspan="3" class="hiddenRow">' +
	'      <div class="accordion-body collapse ' + id + 'Details" id="' + id + '1">' +
	'       <table class="table table-hoover table-condensed table-nonfluid">' +
	'        <tbody>' +
	'         <thead><tr><th>Online</th><th>PDF</th><th>Single Page</th></tr></thead>';
}

function catalogueFooter() {
    return '' +
	'        </tbody>' +
	'       </table>' +
	'      </div>' +
	'     </td>' +
	'    </tr>' +
        '   </tbody>' +
	'  </table>' +
	' </dev/>';
}

function panel_handlers(tag, id, show) {
    $('#' + id + '1').on('shown.bs.collapse', function () {
	$("#" + id + " i.indicator").removeClass("glyphicon-chevron-up").addClass("glyphicon-chevron-down");
	var top = $('#rtems-catalogue-' + tag).offset().top;
	$('html, body').animate({ scrollTop: top }, 500);
    });
    $('#' + id + '1').on('hidden.bs.collapse', function () {
	$("#" + id + " i.indicator").removeClass("glyphicon-chevron-down").addClass("glyphicon-chevron-up");
    });
    if (show == true)
	$('#' + id + '1').collapse('show');
}

function paintCatalogue(xml, path, tag, show) {
    var el_cat = $('#rtems-catalogue-' + tag);
    if (path.slice(-1) != '/')
	path = path + '/';
    /*
     * Use jquery as XMLDocument is consider not stable on Firefox's web site.
     */
    var pdfIcon = 'static/img/Adobe_PDF_file_icon_32x32.png';
    var htmlIcon = 'static/img/html-xxl.png';
    var docs = $(xml).find('rtems-docs');
    var date = $(docs).attr('date');
    var title = $(docs).find('catalogue');
    var id = title.text().replace(/\.| |\(|\)|\[|\]/g, '_');
    var table = catalogueHeader(id, title.text(), date);
    $(docs).find('doc').each(function() {
	var name = $(this).find('name').text();
	var title = $(this).find('title').text();
	var release = $(this).find('release').text();
	var version = $(this).find('version').text();
	var html = $(this).find('html').text();
	var pdf = $(this).find('pdf').text();
	var singlehtml = $(this).find('singlehtml').text();
	var empty = '<td></a></td>\n';
	table += '<tr>\n';
	if (html)
	    table += '<td><a href="' + path + html + '">' + title + '</a></td>\n';
	else
	    table += empty;
	if (pdf)
	    table += '<td><a href="' + path + pdf + '">' +
 	    '<img src="' + pdfIcon + '" width="20" height="20"></a></td>\n';
	else
	    table += empty;
	if (singlehtml)
	    table += '<td><a href="' + path + singlehtml + '">' +
	    '<img src="' + htmlIcon + '" width="20" height="20"></a></td>\n';
	else
	    table += empty;
	table += '</tr>\n';
    });
    table += catalogueFooter();
    el_cat.html(table);
    panel_handlers(tag, id, show);
}

function loadCatalogue(catalogue, path, tag, show) {
    var f = $.get(catalogue, function(xml) {
	paintCatalogue(xml, path, tag, show);
    }, 'xml');
}
