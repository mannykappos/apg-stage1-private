"""Revision 3 (corrected after the independent agent audit of 2026-11-12): the systems builders and developers use, the APG entities their
cited sources support, and how data can be got out.  Evidence levels: docs (the vendor's developer or product documentation), vendor (a
vendor marketing page), third-party (a review site or another vendor's page).  An entity is listed only where the cited source supports
it; judgement beyond the sources is kept in ENTITY_REGISTER.csv's 'likely also (judgement, unverified)' column.  Every row is to be
confirmed with a pilot builder's sample export; none is a coverage promise.  Searched 2026-11-12."""
import csv

S = [
# code, system, category, typical users (as the source says), entities the source supports, access, evidence, source(s), note
('ACC', 'Xero', 'accounting', 'small to mid businesses', 'E15 E20 E23 E24 E25 E73 E79',
 'API: invoices, bills, credit notes, payments, bank transactions, purchase orders, journals (live); bank feed statements and aged debtors and creditors (beta)',
 'third-party (unified-API resource list)', 'https://developers.apideck.com/apis/accounting/xero/resources', 'project or job costing by tracking category; line quantity and rate to confirm in a sample export'),
('ACC', 'MYOB (AccountRight, MYOB Business)', 'accounting', 'small to mid businesses (AU)', 'E15 E20 E23 E25 E79',
 'API (AccountRight and MYOB Business)', 'third-party', 'https://www.apideck.com/blog/how-to-integrate-with-the-myob-api', 'objects to confirm in a sample export'),
('ERP', 'Jobpac Connect (Trimble Viewpoint)', 'construction ERP', 'Australian and New Zealand construction companies (vendor); many mid-to-large firms (third-party)',
 'E09 E13 E15 E16 E19 E21 E23 E41 E81',
 'not stated; integrations exist (Payapps names Jobpac Connect)', 'vendor; third-party',
 'https://info.viewpoint.com/Jobpac-Brand_01-Landing-Page.html ; https://www.mastt.com/glossary/what-is-jobpac',
 'vendor page: job and labour costing, forecasting, subcontractors, payroll, AP, AR; third-party page: variations, progress claims, subcontractor payments, purchase orders, subcontractor agreements'),
('ERP', 'Databuild', 'estimating and job management', 'builders', 'E21 E38 E40', 'not established', 'third-party',
 'https://www.softwareadvice.com.au/software/275036/databuild-estimating-software', 'to confirm with a sample export'),
('BX', 'Buildxact', 'estimating and job management', 'small and mid residential builders', 'E40',
 'API with partner approval (subscription key and bearer token); estimates and catalogues documented, jobs by OData; webhooks',
 'docs', 'https://developer.buildxact.com/getting-started', 'residential focus; not the initial commercial segment'),
('PM', 'Procore', 'project management and project financials', 'large commercial companies', 'E07 E08 E09 E13 E16 E17 E19 E20 E21 E22 E65 E66',
 'API (financial tools: projects, vendors, cost codes, direct costs, commitments, commitment change orders, change events, prime contracts, subcontractor invoices, payment applications, payments)',
 'docs (financials); vendor (RFIs, inspections, quality and defect tracking, variations and progress claims on the AU page)',
 'https://procore.github.io/documentation/tutorial-financial-tools ; https://www.procore.com/en-au/commercial', 'Security of Payment is not mentioned on the AU page; daily logs not established'),
('PM', 'Oracle Aconex', 'document control and correspondence', 'large projects', 'E83',
 'a Mail API exists (developer guide and Swagger linked); what mail types hold is to confirm', 'docs (existence only)', 'https://help.aconex.com/apis/mail-api-developer-guide/',
 'site instructions and notices are likely carried as mail (judgement, in the register), not shown by the cited page'),
('CLM', 'Payapps', 'progress claims (head contract and subcontract)', 'main contractors and subcontractors', 'E09 E13 E14 E17 E18 E75 E82',
 'integrations named: Xero, MYOB, Jobpac Connect, Procore; no API or export described', 'vendor', 'https://www.payapps.com/features/',
 'the nearest system to the claims gap; access to confirm with the vendor'),
('EST', 'RIB CostX', 'takeoff and estimating', 'quantity surveyors and estimators', 'E40', 'Excel integration listed; no API established', 'third-party', 'https://www.capterra.com.au/software/75416/costx', ''),
('SCH', 'Oracle Primavera (P6 XML and XER)', 'programme', 'larger projects', 'E47 E48 E49 E50 E98',
 'P6 XML and XER files (activities, relationships, calendars, WBS, baselines, resources, activity codes)', 'docs (Primavera Cloud import objects for P6 XML/XER)',
 'https://docs.oracle.com/cd/E80480_01/help/en/user/234146.htm', 'actual dates and percent complete not shown on the page; to confirm in a sample file'),
('SCH', 'Microsoft Project', 'programme', 'small to mid builders', '', 'MS Project XML file', 'not checked', '-', 'to confirm with a sample file'),
('SITE', 'HammerTech', 'safety, inductions and site management', 'commercial builders', 'E55 E57',
 'Procore sync of labour hours by trade partner, worker counts and site diaries; no open API described', 'vendor', 'https://www.hammertech.com/en-au/integration-partners/procore',
 'inductions, permits, inspections, observations and workforce compliance are HammerTech workflows the page says are not synced'),
('PAY', 'Employment Hero (KeyPay)', 'payroll and timesheets', 'Australian businesses', '', 'integrations and an API advertised; objects not checked', 'not checked', 'https://www.keypay.com.au/feature/integration', 'to confirm'),
('XLS', 'Excel and Google Sheets', 'spreadsheets', 'common practice (not a sourced figure)', '', 'file import; layouts differ per builder', 'not sourced', '-', 'mapped once per builder layout and checked (the import-template path)'),
('DOC', 'Email and documents (PDF, photos)', 'correspondence and evidence', 'every builder', '', 'email forwarding or upload; values confirmed by a person (S04 s12)', 'APG design', '-', ''),
('DEV', 'EstateMaster', 'development feasibility and management', 'developers, investors and valuers', 'E95', 'not established', 'third-party', 'https://www.mastt.com/glossary/estatemaster',
 'feasibility; actual costs and revenues against feasibility; sales, settlements, finance and holding costs not described'),
('BANK', 'Bank feeds and statements (data source)', 'cash', 'every business', 'E73', 'through the accounting system\'s bank feed, or statement files', 'third-party', 'https://developers.apideck.com/apis/accounting/xero/resources', 'a data source, not a builder system'),
('EXT', 'Market and FX feeds (data source)', 'external reference', 'APG', 'E36 E37', 'APG market intelligence engine', 'APG design', '-', 'a data source, not a builder system'),
]

with open('SYSTEMS_SURVEY.csv', 'w', newline='') as fh:
    w = csv.writer(fh, lineterminator='\n')
    w.writerow(['code', 'system', 'category', 'typical users (as the source says)', 'APG entities the cited source supports (ids in ENTITY_REGISTER.csv)', 'how data can be got out', 'evidence level', 'source(s)', 'note'])
    w.writerows(S)
print('rows', len(S), 'systems', sum(1 for s in S if 'data source' not in s[1]))
