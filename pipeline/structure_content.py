import requests

def safe_string_conversion(value, max_items=5):
    if isinstance(value, list):
        # Convert list items to strings and limit the number of items
        string_items = []
        for item in value[:max_items]:
            if isinstance(item, dict):
                # For dict items, try to get a meaningful string representation
                if 'title' in item:
                    string_items.append(str(item['title']))
                elif 'name' in item:
                    string_items.append(str(item['name']))
                else:
                    string_items.append(str(item)[:100])  # Limit length
            else:
                string_items.append(str(item))
        return ', '.join(string_items)
    elif isinstance(value, dict):
        # For dict, try to get a meaningful string representation
        if 'title' in value:
            return str(value['title'])
        elif 'name' in value:
            return str(value['name'])
        else:
            return str(value)[:100]  # Limit length
    elif value is None:
        return "Not specified"
    else:
        return str(value)

def structure_document_content(url: str):
    try:
        json_data = requests.get(url).json()

        ocr_data = json_data.get("ocr_result", {})
        file_name = json_data.get("file_name", "Unknown")

        xml_content = '<document>\n'
        xml_content += f'  <file_name>{safe_string_conversion(file_name)}</file_name>\n'
        xml_content += f'  <title>{safe_string_conversion(ocr_data.get("document_title", "Unknown"))}</title>\n'
        xml_content += f'  <type>{safe_string_conversion(ocr_data.get("document_type", "Unknown"))}</type>\n'
        xml_content += f'  <total_pages>{safe_string_conversion(ocr_data.get("total_pages", "N/A"))}</total_pages>\n'
        xml_content += f'  <summary>{safe_string_conversion(ocr_data.get("summary", "Unknown"))}</summary>\n'
        
        # Handle key topics as a proper list
        key_topics = ocr_data.get("key_topics", [])
        xml_content += '  <key_topics>\n'
        for topic in key_topics:
            xml_content += f'    <topic>{safe_string_conversion(topic)}</topic>\n'
        xml_content += '  </key_topics>\n'
        
        # Handle table of contents
        toc = ocr_data.get("table_of_contents", [])
        xml_content += '  <table_of_contents>\n'
        if isinstance(toc, list) and toc:
            for item in toc:
                if isinstance(item, dict):
                    # Handle structured table of contents
                    level = item.get('level', 1)
                    title = safe_string_conversion(item.get('title', 'Unknown'))
                    page = safe_string_conversion(item.get('page', 'N/A'))
                    summary = safe_string_conversion(item.get('summary', 'No summary'))
                    subsections = item.get('subsections', [])
                    
                    xml_content += f'    <section level="{level}" page="{page}">\n'
                    xml_content += f'      <title>{title}</title>\n'
                    xml_content += f'      <summary>{summary}</summary>\n'
                    
                    if subsections:
                        xml_content += '      <subsections>\n'
                        for subsection in subsections:
                            if isinstance(subsection, dict):
                                sub_title = safe_string_conversion(subsection.get('title', 'Unknown'))
                                sub_summary = safe_string_conversion(subsection.get('summary', 'No summary'))
                                xml_content += f'        <subsection>\n'
                                xml_content += f'          <title>{sub_title}</title>\n'
                                xml_content += f'          <summary>{sub_summary}</summary>\n'
                                xml_content += f'        </subsection>\n'
                            else:
                                xml_content += f'        <subsection>{safe_string_conversion(subsection)}</subsection>\n'
                        xml_content += '      </subsections>\n'
                    
                    xml_content += f'    </section>\n'
                else:
                    # Handle simple string items
                    xml_content += f'    <item>{safe_string_conversion(item)}</item>\n'
        else:
            xml_content += '    <item>No table of contents available</item>\n'
        xml_content += '  </table_of_contents>\n'
        
        xml_content += '</document>'

        return xml_content
    except Exception as e:
        return {"error": str(e)}
    
def structure_chapters_content(chapter: object, part: str, title: str):
    try:
        xml_content = '<regulations>\n'
        xml_content += f'  <part name="{part}" title="{safe_string_conversion(title)}">\n'
        chapter_num = chapter.get('chapter_num', 'Unknown')
        chapter_title = chapter.get('chapter_title', 'Unknown Chapter')
        xml_content += f'    <chapter number="{chapter_num}" title="{safe_string_conversion(chapter_title)}">\n'
        # Process sections within each chapter
        sections = chapter.get('sections', [])
        for section in sections:
            section_id = section.get('id', 'unknown_section')
            section_title = section.get('title', 'Unknown Section')
            section_content = section.get('content', '')
                    
            xml_content += f'      <section id="{section_id}" title="{safe_string_conversion(section_title)}">\n'
            xml_content += f'        <content>{safe_string_conversion(section_content)}</content>\n'
            xml_content += f'      </section>\n'
                
        xml_content += f'    </chapter>\n'
        xml_content += f'  </part>\n'
        xml_content += '</regulations>'

        return xml_content
        
    except Exception as e:
        return {"error": str(e)}