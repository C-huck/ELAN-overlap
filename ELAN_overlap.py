# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 22:23:47 2020

@author: Jack
"""

from bs4 import BeautifulSoup
import lxml
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
        tier_options = zip(tier_indices,[x[:10]+"..."+x[-5:] if len(x)>20 else x for x in self.tier_names])
        print("The tier names are",[x for x in tier_options])
        print("Enter tier numbers separated by commas (e.g., 0,1,2) or type \"all\" for all tiers")
        sel_tiers = input("Which tiers do you want?: ")
        if sel_tiers == "all":
            self.sel_tiers = self.tier_names
        else:
            sel_tiers = [int(x) for x in sel_tiers.split(",")]
            self.sel_tiers = [self.tier_names[x] for x in sel_tiers]
        print("Fetching annotations, timeslots...")
        self.time_slots, self.annotation_values, self.sel_tiers, self.skipped_tiers = self.get_start_stop(resolution=self.resolution)
        self.last_time_slot = self.get_timeslot_len()
        print("Building matrix")
        self.matrix = self.build_matrix()
        self.matrix,self.matrix_a = self.fill_matrix()
        print("Ready!")

    def eaf_read(self):
        """
        Read in and parse eaf file; find time slots and tier names
        """
        with open(self.fileName,encoding="utf8") as fp:
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
        """
        Translate tier names to tier indices and back
        """
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

    def check_for_parent_tier(self,c):
        """
        Check to see if current tier has a parent tier
        Returns False if tier has a parent tier
        """
        if c[0].ALIGNABLE_ANNOTATION:
            return True
        else:
            return False

    def get_annotation_IDs(self,tier):
        """
        Links child tiers to parent tiers via annotation refs and annotation ids
        """
        annotation_ids = []
        annotation_refs = []
        if len(tier.find_all('REF_ANNOTATION')) > 0:
            for x in tier.find_all('REF_ANNOTATION'):
                annotation_ids.append(x['ANNOTATION_ID'])
                annotation_refs.append(x['ANNOTATION_REF'])
        else:
            for x in tier.find_all('ALIGNABLE_ANNOTATION'):
                annotation_ids.append(x['ANNOTATION_ID'])
                annotation_refs.append(None)
        return annotation_ids,annotation_refs

    def get_parent_tier(self,tiers):
        """
        Retrieve time slot information from parent tier
        Returns parent tier, annotation ids and annotations refs
        """
        parent_ref = tiers[0]['PARENT_REF']
        parent_tier = self.soup.find_all('TIER',TIER_ID=parent_ref)
        if parent_tier[0].ALIGNABLE_ANNOTATION:
            _,annotation_refs = self.get_annotation_IDs(tiers[0])
            annotation_ids,_ = self.get_annotation_IDs(parent_tier[0])
            return parent_tier, set(annotation_ids) & set(annotation_refs)
        else:
            parent_tier = self.get_parent_tier(parent_tier)
            return parent_tier

    def get_start_stop(self,resolution=1000):
        """
        Retrieve start and end times for each annotation on each tier
        Returns the annotation value and time slots for each annotation on each tier
        """
        time_slots=[]
        annotation_values=[]
        new_sel_tiers = []
        skipped_tiers = []
        for i in range(len(self.sel_tiers)):
            tiers = self.soup.find_all('TIER',TIER_ID=self.sel_tiers[i])
            c = tiers[0].find_all('ANNOTATION')
            start = []
            annote = []
            if len(c) == 0:
                #print("No annotations on {}. Skipping.".format(self.sel_tiers[i]))
                skipped_tiers.append(self.sel_tiers[i])
            else:
                new_sel_tiers.append(self.sel_tiers[i])
                if self.check_for_parent_tier(c):
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
                else:
                    parent_tier, annot_IDs = self.get_parent_tier(tiers)
                    parent_tier_annot = parent_tier[0].find_all('ANNOTATION')
                    for i,y in enumerate(annot_IDs):
                        for j in range(len(parent_tier_annot)):
                            if len(parent_tier_annot[j].find_all('ALIGNABLE_ANNOTATION',ANNOTATION_ID=y)) > 0:
                                parent_annot = parent_tier_annot[j].find_all('ALIGNABLE_ANNOTATION',ANNOTATION_ID=y)
                                e = [s['TIME_SLOT_REF1'] for s in parent_annot][0]
                                ee = [s['TIME_SLOT_REF2'] for s in parent_annot][0]
                                for f in self.master_ts:
                                    if f["TIME_SLOT_ID"] == e:
                                        g = int(round(int(f["TIME_VALUE"])/resolution,0))
                                    if f["TIME_SLOT_ID"] == ee:
                                        gg = int(round(int(f["TIME_VALUE"])/resolution,0))
                                start.append([[int(s['TIME_SLOT_REF1'][2:]) for s in parent_annot][0],[int(s['TIME_SLOT_REF2'][2:]) for s in parent_annot][0],g,gg])
                                annote.append(c[i].ANNOTATION_VALUE.string)
                            else:
                                continue
                    time_slots.append(start)
                    annotation_values.append(annote)
                print('\r',round(i/len(self.sel_tiers)*100),' percent complete', end='')
                print('\r', end='')
        print("100")
        if len(skipped_tiers) > 0:
            print("{} tiers did not contain annotations and were skipped.".format(len(skipped_tiers)))
        return time_slots, annotation_values, new_sel_tiers, skipped_tiers

    def get_timeslot_len(self):
        """
        Returns last time slot in eaf file
        """
        return int(self.master_ts[-1]['TIME_VALUE'])

    def build_matrix(self):
        """
        Builds an empty matrix of 0's according to the size and temporal resolution of the input ELAN file
        """
        return np.zeros((len(self.sel_tiers),self.last_time_slot), dtype=int)

    def fill_matrix(self):
        """
        Builds two matrices: one with duration information and one with annotations
        """
        matrix_a = np.copy(self.matrix).astype(str)
        for k in range(len(self.matrix)):
            for i,x in enumerate(self.time_slots[k]):
                if len(x) > 0:
                    num_str= [13] + [12]*(int(x[3])-int(x[2])) + [-13]
                    np.put(self.matrix[k],range(int(x[2])-1,int(x[3])),num_str)
                    np.put(matrix_a[k],range(int(x[2])-1,int(x[3])),self.annotation_values[k][i])
            print('\r',round(k/len(self.matrix)*100),' percent complete', end='')
            print('\r', end='')
        print("100 ")
        return self.matrix, matrix_a

    def overlap_relationships(self,base,ref):
        """
        For any two tiers, reports overlaps, type of overlap (e.g., contains, is contained by, etc.), and overlap duration
        """
        results =[]
        for i,y in enumerate(self.time_slots[base]):
            for ii,yy in enumerate(self.time_slots[ref]):
                if y[0] < yy[0] and y[1] > yy[1]: #containment
                    results.append([self.annotation_values[base][i],self.annotation_values[ref][ii],"contains",yy[3]-yy[2]])
                elif yy[0] < y[0] and yy[1] > y[1]:  #contained-by
                    results.append([self.annotation_values[base][i],self.annotation_values[ref][ii],"contained by",y[3]-y[2]])
                elif yy[0] > y[0] and y[1] > yy[0] and yy[1] > y[1]:  #right edge contained
                    results.append([self.annotation_values[base][i],self.annotation_values[ref][ii],"right edge",y[3]-yy[2]])
                elif yy[0] < y[0] and y[0] < yy[1] and yy[1] < y[1]:  #left edge contained
                    results.append([self.annotation_values[base][i],self.annotation_values[ref][ii],"left edge",yy[3]-y[2]])
                elif y[0] == yy[0] and y[1] == yy[1]: #isometric:
                    results.append([self.annotation_values[base][i],self.annotation_values[ref][ii],"isometric",y[3]-y[2]])
        results = pd.DataFrame(data=results,columns=["Annotation Val. 1","Annotation Val. 2","Overlap Type","Duration overlap"])
        print(results)
        return results

    def get_overlap_durations(self,hits):
        """
        Computes duration of overlap at time denoted by 'hits'
        """
        durations = []
        for x in hits:
            i = 0
            while self.matrix[:,x+1+i].sum() == (len(self.sel_tiers)*12):
                i+=1
            durations.append(i)
        return durations

    def get_threshhold(self,vector):
        """
        Computes a threshhold set at one standard deviation below the mean of 'vector'
        """
        mean = np.mean(vector)
        std = np.std(vector)
        return mean - std

    def prune_short_annotations(self,hits):
        """
        Excludes overlaps that are shorter than a given temporal threshhold
        """
        g = input("Enter threshhold (in units per your temporal resolution) or choose 'auto': ")
        durations = self.get_overlap_durations(hits)
        if g == "auto":
            threshhold = self.get_threshhold(durations)
        else:
            threshhold = int(g)
        return [y for (x,y) in zip(durations,hits) if x > threshhold]

    def pretty_print(self,df,sel_tiers):
        """
        Helper function to display results neatly in console
        """
        if type(sel_tiers) == int:
            col_names = self.sel_tiers[sel_tiers]
        else:
            col_names = [self.sel_tiers[j] for j in sel_tiers]
        df[col_names] = df['index'].str.split("|",expand=True)
        df = df.drop(["index"],axis=1)
        df = df.rename(columns={0:"Frequency"})
        shorten = lambda x: x[:10]+x[:-5] if len(x) > 20 else x
        return df.rename(shorten,axis='columns')

    def overlapping_annotations(self,hits,matrix):
        overlapped_annots = []
        for j in hits:
            per_tier = [str(x[j]) for x in matrix]
            overlapped_annots.append("|".join(per_tier))
        if len(overlapped_annots) == 0:
            return None
        else:
            return Counter(overlapped_annots)

    def overlaps(self,matrix,sel_tiers):
        """
        Finds overlaps using left edge of annotations
        """
        prune = input("Exclude short overlaps from consideration?: [y/n] ")
        hits = np.where(np.sum(matrix[sel_tiers],axis=0) > max((len(sel_tiers)-1)*13,(len(sel_tiers)*12)))
        hits = np.array(hits).tolist()[0]
        if prune == "y":
            hits = self.prune_short_annotations(hits)
        return hits

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
        if len(string_matches) == 0:
            print("No annotation matches your term")
        else:
            if len(search_tiers) == 1:
                #hits = np.nonzero(self.matrix[[tier]+search_tiers])
                #hits = np.array(hits).tolist()[0]
                hits = self.overlaps(self.matrix,[tier]+search_tiers)
            else:
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
    while True:
        try:
            choice = int(input("Index #: "))
            choice = choices[choice][1]
            fileOut = choice.split(".")[0]
            break
        except:
            print("Choice must be a single integer")
            continue

    print("At what temporal resolution should we reconstruct the eaf?")
    try:
        resolution = int(input("Enter integer (in msec): "))
    except:
        print("Choice must be a single integer")
    ELAN_file = AnnotationObject(choice,resolution)
    function_options = [(0, 'Get annotations'), (1, 'Get overlaps'), (2, 'Word Search'), (3, 'Get overlap relationships'), (4, 'See selected tiers'), (5, 'See empty tiers'), (6,'Quit')]
    tier_options = list(zip(list(range(len(ELAN_file.sel_tiers))),[x[:10]+"..."+x[-5:] if len(x)>20 else x for x in ELAN_file.sel_tiers]))
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
            #ELAN_file.reset()
            print("Which tiers would you like? (Choose 2)")
            print(tier_options)
            sel_tiers = input("Enter each tier ID# separated by a comma: ")
            try:
                sel_tier_ints = [int(x) for x in sel_tiers.split(",")]
            except:
                print("Invalid input")
                continue
            ELAN_file.overlap_relationships(sel_tier_ints[0],sel_tier_ints[1])
        if function_choice == 4:
            print(ELAN_file.sel_tiers)
            continue
        if function_choice == 5:
            print(ELAN_file.skipped_tiers)
            continue
        if function_choice == 6:
            del ELAN_file
            break
