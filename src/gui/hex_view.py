import tkinter as tk

class HexView(tk.Text):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.config(state='disabled', font=("Courier", 10))
        self.tag_configure("highlight", background="yellow", foreground="black")
        
    def load_data(self, data: bytes):
        self.config(state='normal')
        self.delete('1.0', tk.END)
        
        # Format:
        # Offset   Hex................................  Ascii
        # 00000000 00 01 02 03 04 05 06 07  08 09 0A 0B 0C 0D 0E 0F  |................|
        
        lines = []
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            
            # Hex part
            hex_part = []
            for j, b in enumerate(chunk):
                hex_part.append(f"{b:02X}")
                if j == 7: # Extra space
                    hex_part.append("")
            
            # Pad hex part if last line is short
            if len(chunk) < 16:
                padding = 16 - len(chunk)
                # 3 chars per byte + 1 space for 8th byte if missing
                # Actually simplest way is just to fill hex_part list
                pass
            
            hex_str = " ".join(hex_part).ljust(49) # 16*3 + 1 = 49
            
            # Ascii part
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            
            lines.append(f"{i:08X}  {hex_str}  |{ascii_part}|")
            
        self.insert('1.0', "\n".join(lines))
        self.config(state='disabled')
        
    def highlight_range(self, start: int, end: int):
        self.tag_remove("highlight", "1.0", tk.END)
        
        if start >= end:
            return
            
        # Convert offset to line.col
        # Each line represents 16 bytes
        # Line 1 corresponds to offset 0-15
        
        current_off = start
        while current_off < end:
            line_idx = (current_off // 16) + 1
            col_idx = current_off % 16
            
            # Calculate range on this line
            line_start_off = (line_idx - 1) * 16
            line_end_off = line_start_off + 16
            
            chunk_end = min(end, line_end_off)
            
            # Calculate text column positions
            # Offset (8) + 2 spaces = 10 chars
            # Each byte is 3 chars ("XX ")
            # Extra space after 8th byte (index 7)
            
            def get_text_col(byte_idx):
                col = 10 + (byte_idx * 3)
                if byte_idx >= 8:
                    col += 1
                return col
                
            start_col = get_text_col(col_idx)
            end_col = get_text_col(chunk_end - line_start_off)  # End is exclusive implies we want up to the start of next byte?
            # Actually we highlight the hex digits. "XX " is 3 chars. highlighting "XX" is 2 chars.
            # So end_col should be carefully calculated.
            
            # Simpler: highlight "XX " for each byte in range
            for b_idx in range(col_idx, chunk_end - line_start_off):
                c_start = get_text_col(b_idx)
                c_end = c_start + 2 # Highlight just the 2 digits
                self.tag_add("highlight", f"{line_idx}.{c_start}", f"{line_idx}.{c_end}")
            
            current_off = chunk_end
        
        self.see(f"{(start // 16) + 1}.0")
