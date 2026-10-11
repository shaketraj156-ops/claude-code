"""English and Hindi brief generation shared by site and consolidated exports."""
SITE_HI = {
    'Bairagarh (Sant Hirdaram) kund': 'बैरागढ़ (संत हिरदाराम) कुंड',
    'Khatlapura ghat': 'खटलापुरा घाट',
    'Prempura ghat': 'प्रेमपुरा घाट',
    'Rani Kamlapati ghat / Kamla Park kund': 'रानी कमलापति घाट / कमला पार्क कुंड',
    'Hathaikheda dam / kund': 'हथाईखेड़ा बाँध / कुंड',
    'Malikhedi kund': 'मालिखेड़ी कुंड',
    'Shahpura lake ghat': 'शाहपुरा झील घाट',
}
FESTIVAL_HI = {'Ganesh': 'गणेश', 'Durga': 'दुर्गा'}
FESTIVAL_ORDER = {'Ganesh': 0, 'Durga': 1}
PARAMETER_HI = {'pH': 'अम्लता-क्षारीयता (पीएच)', 'Dissolved oxygen': 'घुलित ऑक्सीजन', 'BOD': 'जैव रासायनिक ऑक्सीजन माँग'}
PHASE_HI = {'pre': 'विसर्जन से पहले', 'during': 'विसर्जन के दौरान', 'after': 'विसर्जन के बाद'}
PHASE_EN = {'pre': 'before immersion', 'during': 'during immersion', 'after': 'after immersion'}


def site_name(group, hindi=False):
    # Unknown proper names stay verbatim unless the uploader supplies site_hi.
    return SITE_HI.get(group['site'], group.get('site_hi') or group['site']) if hindi else group['site']


def limit_text(value, hindi=False):
    return value.replace('mg/l', 'मि.ग्रा./लीटर') if hindi else value


def evidence(row, hindi=False):
    if not row:
        return 'कोई माप उपलब्ध नहीं' if hindi else 'No reading available'
    if row.get('report') and row.get('source_page'):
        if hindi:
            title = 'मूर्ति विसर्जन रिपोर्ट' if row['year'] == 2023 else 'गणेश एवं दुर्गा विसर्जन रिपोर्ट'
            return f'{title} {row["year"]}, पृष्ठ {row["source_page"]}'
        return f'{row["report"]}, PDF p. {row["source_page"]}'
    if hindi:
        text = 'अपलोड किए गए साक्ष्य का साथ दी गई रिपोर्टों से मिलान नहीं हुआ'
        document = row.get('source_document_hi') or row.get('source_document', '')
        return text + (f'; उपयोगकर्ता का मूल स्रोत-विवरण: {document}' if document else '')
    document = row.get('source_document', '').strip()
    return 'Uploaded source not matched to bundled reports' + (f': {document}' if document else '')


def scope_label(view, hindi=False):
    years = sorted({e['year'] for g in view['sites'] for e in g['events']})
    # Calendar order, matching the filters and the rest of the app, not alphabetical.
    festivals = sorted({e['festival'] for g in view['sites'] for e in g['events']},
                       key=lambda f: (FESTIVAL_ORDER.get(f, 9), f))
    if hindi:
        festivals = [FESTIVAL_HI.get(f, f) for f in festivals]
    return f'{", ".join(map(str, years))} · {", ".join(festivals)}'


def reading_description(row, limits, hindi=False):
    p = row['parameter']
    if hindi:
        unit = '' if p == 'pH' else ' मि.ग्रा./लीटर'
        return f'{PARAMETER_HI[p]} {row["value"]}{unit}; {FESTIVAL_HI.get(row["festival"], row["festival"])} {row["year"]}, {PHASE_HI[row["phase"]]}; संदर्भ {limit_text(limits[p], True)}।'
    unit = '' if p == 'pH' else ' mg/l'
    return f'{p} {row["value"]}{unit}; {row["festival"]} {row["year"]}, {PHASE_EN[row["phase"]]}; reference {limits[p]}.'


def method_note(hindi=False):
    return ('क्रम का आधार: संदर्भ न्यूनतम से कम घुलित ऑक्सीजन वाले स्थल पहले; इनमें न्यूनतम ऑक्सीजन जितनी कम, प्राथमिकता उतनी अधिक। समान न्यूनतम पर कम ऑक्सीजन की आवृत्ति, फिर अन्य उल्लंघनों की तीव्रता और आवृत्ति देखी जाती है। यह परियोजना की प्राथमिकता विधि है, आधिकारिक जोखिम वर्गीकरण नहीं।'
            if hindi else 'Ranking rule: sites with below-reference dissolved oxygen come first, ordered by lowest oxygen, then low-oxygen frequency, then other breach severity and frequency. This is a project priority method, not an official risk classification.')


def caveats(limits, hindi=False):
    references = '; '.join(f'{PARAMETER_HI[p] if hindi else p}: {limit_text(value, hindi)}' for p, value in limits.items())
    if hindi:
        return f'संदर्भ: श्रेणी बी; {references}। इकाइयाँ मानी गई हैं। कुल कोलीफॉर्म उपलब्ध नहीं; यह पूर्ण अनुपालन या वर्तमान सुरक्षा का प्रमाण नहीं है। पहचान सीमा से नीचे या न पाए गए मानों को शून्य नहीं माना गया है। यह ऐतिहासिक प्राथमिकता है, पूर्वानुमान नहीं।'
    return f'Reference: Class B; {references}. Units are assumed. Total coliform is unavailable; this is not full compliance or current safety certification. BDL/ND are not zero. This is historical prioritisation, not a forecast.'


def make_site_brief(group, view, language='en'):
    hi = language == 'hi'
    g = group
    lines = [site_name(g, hi) + (' — स्थल संक्षेप' if hi else ' — site brief'), scope_label(view, hi)]
    if hi:
        lines += [f'{g["assessed"]} आकलित मानों में से {g["breaches"]} संदर्भ सीमा से बाहर; {g["expected"]} अपेक्षित जाँचों में से {g["missing"]} का आकलन नहीं हो सका।',
                  f'दर्ज प्रदूषण प्राथमिकता: {g["pollution_rank"] or "आकलन नहीं"}; नई जाँच प्राथमिकता: {g["testing_rank"]}।']
    else:
        lines += [f'{g["breaches"]}/{g["assessed"]} assessed readings outside reference; {g["missing"]}/{g["expected"]} expected checks unassessed.',
                  f'Pollution rank: {g["pollution_rank"] or "unranked"}; fresh testing rank: {g["testing_rank"]}.']
    priority = g['priority_reading']
    if priority:
        lines += [('प्राथमिकता का प्रमुख साक्ष्य: ' if hi else 'Priority evidence: ') + reading_description(priority, view['limits'], hi),
                  ('स्रोत: ' if hi else 'Source: ') + evidence(priority, hi)]
    if g['identity_uncertain']:
        lines.append('स्थल की पहचान की पुष्टि करें: सभी रिकॉर्ड एक ही स्थान के हैं या नहीं, इसकी जाँच आवश्यक है।' if hi else 'Site identity needs confirmation: check that these records refer to the same place.')
    if hi:
        lines.append(f'साक्ष्य: {g["row_count"]} दर्ज मानों में से {g["matched_sources"]} साथ दिए गए रिपोर्ट डेटा से मेल खाते हैं।')
        if g['matched_sources'] < g['row_count']:
            lines.append('अन्य अपलोड किए गए मानों के मूल प्रयोगशाला या रिपोर्ट प्रमाण की जाँच करें।')
        lines += [f'विसर्जन के बाद {g["after_assessed"]} आकलित मानों में से {g["after_breaches"]} सीमा से बाहर हैं।',
                  'अगला कदम: वर्तमान नमूने लें और सफाई तथा पानी में हवा पहुँचाने की आवश्यकता की अधिकारी से समीक्षा कराएँ।']
    else:
        lines.append(f'Evidence: {g["matched_sources"]}/{g["row_count"]} recorded rows match bundled reports.')
        if g['matched_sources'] < g['row_count']:
            lines.append('Uploaded source not matched for the other rows; verify their laboratory/report evidence.')
        lines += [f'After-immersion readings: {g["after_breaches"]}/{g["after_assessed"]} assessed outside reference.',
                  'Follow-up: obtain current samples and ask the officer to review cleaning/aeration needs.']
    lines += [method_note(hi), caveats(view['limits'], hi)]
    return '\n\n'.join(lines)


def make_brief(view, language='en'):
    hi = language == 'hi'
    lines = [('विसर्जन घाट वॉच — अधिकारी संक्षेप' if hi else 'Visarjan Ghat Watch — officer brief'), scope_label(view, hi)]
    lines.append(f'{view["site_count"]} स्थल; {view["assessed"]}/{view["expected"]} मुख्य जाँचों का आकलन; {view["breaches"]} मान संदर्भ सीमा के बाहर।' if hi else f'{view["site_count"]} sites; {view["assessed"]}/{view["expected"]} core checks assessed; {view["breaches"]} readings outside reference.')
    lines.append(method_note(hi))
    by_site = {g['site']: g for g in view['sites']}
    lines.append('\nदर्ज प्रदूषण के आधार पर प्राथमिकता:' if hi else '\nPriority from recorded breaches:')
    concerning = [by_site[name] for name in view['pollution_order'] if by_site[name]['breaches']]
    for g in concerning[:3]:
        priority = g['priority_reading']
        lines += [f'{g["pollution_rank"]}. {site_name(g, hi)}: ' + reading_description(priority, view['limits'], hi),
                  ('   स्रोत: ' if hi else '   Source: ') + evidence(priority, hi)]
    if not concerning:
        lines.append('उपलब्ध मानों में सीमा का उल्लंघन दर्ज नहीं है; यह सुरक्षा प्रमाण नहीं है।' if hi else 'No breaches in assessed readings; this is not a safety certification.')
    lines.append('\nनई जाँच की प्राथमिकता:' if hi else '\nFresh testing priority:')
    for name in view['testing_order'][:3]:
        g = by_site[name]
        latest = g['latest_year'] or ('उपलब्ध नहीं' if hi else 'unavailable')
        lines.append(f'{g["testing_rank"]}. {site_name(g, hi)}: {g["missing"]}/{g["expected"]} ' + (f'जाँचों का आकलन नहीं; अंतिम संख्यात्मक साक्ष्य वर्ष {latest}।' if hi else f'checks unassessed; latest numeric evidence year {latest}.'))
    ambiguous = [site_name(g, hi) for g in view['sites'] if g['identity_uncertain']]
    if ambiguous:
        lines.append(('\nस्थल पहचान की पुष्टि करें: ' if hi else '\nConfirm site identity: ') + '; '.join(ambiguous))
    lines.append('\nअगला कदम: प्राथमिकता वाले स्थलों पर नए नमूने लें और सफाई तथा पानी में हवा पहुँचाने की आवश्यकता की अधिकारी से समीक्षा कराएँ।' if hi else '\nNext step: obtain fresh samples at priority sites and ask the officer to review cleaning/aeration needs.')
    lines.append(caveats(view['limits'], hi))
    return '\n'.join(lines)
