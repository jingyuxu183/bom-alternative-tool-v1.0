from frontend import render_ui
from backend import get_alternative_parts, process_bom_file, batch_get_alternative_parts

def main():
    render_ui(get_alternative_parts)

if __name__ == "__main__":
    main()