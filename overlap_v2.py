# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 22:23:47 2020

@author: Jack
"""

from bs4 import BeautifulSoup
from collections import Counter
import numpy as np
import pandas as pd
from glob import glob
from itertools import combinations

class AnnotationObject:
    def __init__(self, fileName,resolution):
        self.fileName = fileName
        self.resolution = resolution
        self.tier_names,self.master_ts,self.soup = self.eaf_read()
        tier_indices = list(range(len(self.tier_names)))
        tier_options = zip(tier_indices,self.tier_names)
        print("The tier names are",[x for x in tier_options])
        #sel_tiers = [int(x) for x in input("Which tiers do you want?:").split(",")]
        print("Enter tier numbers separated by commas (e.g., 0,1,2) or type \"all\" for all tiers")
        sel_tiers = input("Which tiers do you want?: ")
        if sel_tiers == "all":
            self.sel_tiers = self.tier_names
        else:
            sel_tiers = [int(x) for x in sel_tiers.split(",")]
            self.sel_tiers = [self.tier_names[x] for x in sel_tiers]
        print("Fetching annotations, timeslots...")
        self.time_slots, self.annotation_values = self.get_start_stop(resolution=self.resolution)
        self.last_time_slot = self.get_timeslot_len()
        print("Building matrix")
        self.matrix = self.build_matrix()
        self.matrix,self.matrix_a = self.fill_matrix()
        print("Ready!")
        
    def eaf_read(self):
        with open(self.fileName) as fp:
            xml_doc = fp.read()
            fp.close()
        #parse xml file, create soup
        soup= BeautifulSoup(xml_doc, "lxml-xml")
        #FIND TIME SLOTS
        master_ts = soup.find_all("TIME_SLOT")
        #FIND TIER NAMES
        a = soup.find_all("TIER")
        tier_names = [s['TIER_ID'] for s in a]
        return tier_names,master_ts,soup
    
    def tier_translate(self,in_list):
        if type(in_list) == list:
            if type(in_list[0]) == int:
                out_list = [self.sel_tiers[q] for q in in_list]
            elif type(in_list[0]) == str:
                out_list = [self.sel_tiers.index(q) for q in in_list]
        else:
            if type(in_list) == int:
                out_list = self.sel_tiers[in_list]
            else:
                out_list = self.sel_tiers.index(in_list)
        return out_list

    def get_start_stop(self,resolution=1000):
        time_slots=[]
        annotation_values=[]
        for i in range(len(self.sel_tiers)):
            tiers = self.soup.find_all('TIER',TIER_ID=self.sel_tiers[i])
            c = tiers[0].find_all('ANNOTATION')
            start = []
            annote = []
            for j in range(len(c)):
                d = c[j].find_all('ALIGNABLE_ANNOTATION')
                e = [s['TIME_SLOT_REF1'] for s in d][0]
                ee = [s['TIME_SLOT_REF2'] for s in d][0]
                for f in self.master_ts:
                    if f["TIME_SLOT_ID"] == e:
                        g = int(round(int(f["TIME_VALUE"])/resolution,0))
                    if f["TIME_SLOT_ID"] == ee:
                        gg = int(round(int(f["TIME_VALUE"])/resolution,0))
                start.append([[int(s['TIME_SLOT_REF1'][2:]) for s in d][0],[int(s['TIME_SLOT_REF2'][2:]) for s in d][0],g,gg])
                annote.append(d[0].ANNOTATION_VALUE.string)
            time_slots.append(start)
            annotation_values.append(annote)
            print('\r',round(i/len(self.sel_tiers)*100),' percent complete', end='')
            print('\r', end='')
        print("100")
        return time_slots, annotation_values
    
    def get_timeslot_len(self):
        return int(self.master_ts[-1]['TIME_VALUE'])

    def build_matrix(self):
        return np.zeros((len(self.sel_tiers),self.last_time_slot), dtype=int)
    
    def fill_matrix(self):
        matrix_a = np.copy(self.matrix).astype(str)
        for k in range(len(self.matrix)):
            for i,x in enumerate(self.time_slots[k]):
                if len(x) > 0:
                    num_str= [13] + [12]*(int(x[3])-int(x[2])) + [-13]
                    np.put(self.matrix[k],range(int(x[2])-1,int(x[3])),num_str)
                    #np.put(self.matrix[k],range(int(x[2])-1,int(x[3])+1),num_str)
                    np.put(matrix_a[k],range(int(x[2])-1,int(x[3])),self.annotation_values[k][i])
                    #np.put(matrix_a[k],range(int(x[2])-1,int(x[3])+1),self.annotation_values[k][i])
            print('\r',round(k/len(self.matrix)*100),' percent complete', end='')
            print('\r', end='')
        print("100 ")
        return self.matrix, matrix_a
    
    def overlaps(self,matrix,sel_tiers):
        prune = input("Exclude short overlaps from consideration?: [y/n] ")
        hits = np.where(np.sum(matrix[sel_tiers],axis=0) > max((len(sel_tiers)-1)*13,(len(sel_tiers)*12)))
        hits = np.array(hits).tolist()[0]
        if prune == "y":
            hits = self.prune_short_annotations(hits)
        return hits

    def get_overlap_durations(self,hits):
        durations = []
        for x in hits:
            i = 0
            while self.matrix[:,x+1+i].sum() == (len(self.sel_tiers)*12):
                i+=1
            durations.append(i)
        return durations
    
    def get_threshhold(self,vector):
        mean = np.mean(vector)
        std = np.std(vector)
        return mean - std

    def prune_short_annotations(self,hits):
        g = input("Enter threshhold (in units per your temporal resolution) or choose 'auto': ")
        durations = self.get_overlap_durations(hits)
        if g == "auto":
            threshhold = self.get_threshhold(durations)
        else:
            threshhold = int(g)
        return [y for (x,y) in zip(durations,hits) if x > threshhold]
    
    def overlapping_annotations(self,hits,matrix):
        overlapped_annots = []
        for j in hits:
            per_tier = [str(x[j]) for x in matrix]
            overlapped_annots.append("|".join(per_tier))
        if len(overlapped_annots) == 0:
            return None
        else:
            return Counter(overlapped_annots)
    
    def pretty_print(self,df,sel_tiers):
        if type(sel_tiers) == int:
            col_names = self.sel_tiers[sel_tiers]
        else:
            col_names = [self.sel_tiers[j] for j in sel_tiers]
        df[col_names] = df['index'].str.split("|",expand=True)
        df = df.drop(["index"],axis=1)
        df = df.rename(columns={0:"Frequency"})
        return df

    def word_search(self,tier,term,search_tiers="all",substring=False):
        if type(tier) == str:
            tier = self.tier_translate(tier)
        if search_tiers == "all":
            search_tiers = list(range(len(self.sel_tiers)))
        else:
            if type(search_tiers[0]) == str:
                search_tiers = self.tier_translate(search_tiers)
        if substring:
            string_matches = np.flatnonzero(np.char.find(self.matrix_a[tier],term) !=-1).tolist()
        else:
            string_matches = np.where(self.matrix_a[tier]==term)[0].tolist()
        hits = self.overlaps(self.matrix,search_tiers)
        matches = self.compare_lists(string_matches,hits)
        if len(matches) > 0:
            if search_tiers=="all":
                result = self.overlapping_annotations(matches,self.matrix_a)
                sel_tiers = list(range(len(self.sel_tiers)))
            else:
                search_tiers = [tier] + search_tiers
                result = self.overlapping_annotations(matches,self.matrix_a[search_tiers])
                sel_tiers = search_tiers
            print("Found "+str(len(result))+" unique hits!")
            df_final = pd.DataFrame.from_dict(result, orient='index').reset_index()
            df_final = self.pretty_print(df_final,sel_tiers)
            print(df_final)
            return df_final
        else:
            print("No overlaps found")
    
    def get_annot_count(self,tier,term=None):
        if term == None:
            string_matches = np.where(self.matrix_a[tier]!="0")[0].tolist()
        else:
            string_matches = np.where(self.matrix_a[tier]==term)[0].tolist()
        num_matches = np.where(self.matrix[tier]==13)[0].tolist()
        matches = self.compare_lists(string_matches,num_matches)
        return len(matches)
        
    
    def avg_word_len(self,tier,term=None):
        if term == None:
            string_matches = np.where(self.matrix_a[tier]!="0")[0].tolist()
        else:
            string_matches = np.where(self.matrix_a[tier]==term)[0].tolist()
        num_matches = np.where(self.matrix[tier]==13)[0].tolist()
        total_len = len(string_matches)
        matches = self.compare_lists(string_matches,num_matches)
        if len(matches) > 0:
            return total_len/len(matches)
        else:
            return "No matches"
    
    def compare_lists(self,a,b):
        a = set(a)
        b = set(b)
        return list(a & b)
    
    def get_annotations(self,tier):
        annotations = [x for x in self.annotation_values[tier]]
        annotations = Counter(annotations)
        df = pd.DataFrame.from_dict(annotations, orient='index').reset_index()
        df = self.pretty_print(df,tier)
        return df
    
    def get_overlaps(self,sel_tiers,matrix=None,matrix_a=None,iterate=False):
        if matrix == None:
            matrix = self.matrix
        if matrix_a == None:
            matrix_a = self.matrix_a
        if type(sel_tiers[0]) == str:
            sel_tiers = self.tier_translate(sel_tiers)
        if iterate:
            combos = []
            dfs = []
            for i in range(1,len(sel_tiers)+1):
                combos+=list(combinations(sel_tiers,i))
            for x in combos:
                x = list(x)
                if len(x) == 1:
                    df = self.get_annotations(x[0])
                    print(df)
                else:
                    hits = self.overlaps(matrix,x)
                    results = self.overlapping_annotations(hits,matrix_a[x])
                    if results == None:
                        print("No overlaps for combination, ",self.tier_translate(list(x)))
                    else:
                        df = pd.DataFrame.from_dict(results, orient='index').reset_index()
                        df = self.pretty_print(df,x)
                        print(df)
                        dfs.append(df)
            return dfs
        else:
            hits = self.overlaps(matrix,sel_tiers)
            results = self.overlapping_annotations(hits,matrix_a[sel_tiers])
            if results == None:
                print("No overlaps detected")
            else:
                df = pd.DataFrame.from_dict(results, orient='index').reset_index()
                df = self.pretty_print(df,sel_tiers)
                print(df)
                return df
        
    
    def reset(self):
        self.__init__(self.fileName,self.resolution)
    
    def __del__(self): 
        print('Deleted ELAN file information')

def fileChooser():
    fileList = glob("*.eaf")
    numList = list(range(len(fileList)))
    return list(zip(numList,fileList))
    

if __name__ == '__main__' :
    print("Choose an input file by selecting its index")
    choices = fileChooser()
    print(choices)
    try:
        choice = int(input("Index #: "))
        choice = choices[choice][1]
        fileOut = choice.split(".")[0]
    except:
        print("Choice must be a single integer")
    print("At what temporal resolution should we reconstruct the eaf?")
    try:
        resolution = int(input("Enter integer (in msec): "))
    except:
        print("Choice must be a single integer")
    ELAN_file = AnnotationObject(choice,resolution)
    function_options = [(0, 'Get annotations'), (1, 'Get overlaps'), (2, 'Word Search'), (3, 'Start over'), (4,'Quit')]
    tier_options = list(zip(list(range(len(ELAN_file.sel_tiers))),ELAN_file.sel_tiers))
    while True:
        print("Available functions: ",function_options)
        try:
            function_choice = int(input("Choose index # of function: "))
        except:
            print("Invalid input")
            continue
        if function_choice == 0:
            print("Which tier would you like?")
            print(tier_options)
            sel_tiers = input("Enter tier ID#: ")
            extension = "get_annot_"+sel_tiers+".csv"
            try:
                sel_tiers = int(sel_tiers)
            except:
                print("Invalid input")
                continue
            df = ELAN_file.get_annotations(sel_tiers)
            print(df)
            df.to_csv(fileOut+extension,index=False)
        if function_choice == 1:
            print("Which tiers would you like?")
            print(tier_options)
            sel_tiers = input("Enter each tier ID# separated by a comma: ")
            try:
                sel_tier_ints = [int(x) for x in sel_tiers.split(",")]
            except:
                print("Invalid input")
                continue
            iterate = input("Get overlaps for all possible combinations of tiers? [y/n]: ")
            if iterate == "y":
                iterate = True
            else:
                iterate = False
            df = ELAN_file.get_overlaps(sel_tier_ints,iterate=iterate)
            if type(df) == list:
                for i,x in enumerate(df):
                    x.to_csv(fileOut+str(i)+".csv",index=False)
            else:
                extension = "overlaps_"+sel_tiers.replace(",","_")+".csv"
                df.to_csv(fileOut+extension,index=False)
        if function_choice == 2:
            print("Which tier does your term appear in?")
            print(tier_options)
            sel_tiers = input("Enter tier ID#: ")
            try:
                sel_tiers = int(sel_tiers)
            except:
                print("Invalid input")
                continue
            search_term = input("What is your search term? (Case sensitive for now): ")
            print("Which tiers would you like to search?")
            search_teirs = input("Enter Tier ID# separated by commas, or type 'all': ")
            if search_teirs!="all":
                try:
                    search_teirs = [int(x) for x in search_teirs.split(",")]
                except:
                    print("Invalid input")
            substring = input("Search for substrings? [y/n]")
            if substring == "y":
                substring = True
            else:
                False
            ELAN_file.word_search(sel_tiers,search_term,search_tiers=search_teirs,substring=substring)
        if function_choice == 3:
            ELAN_file.reset()
        if function_choice == 4:
            del ELAN_file
            break
